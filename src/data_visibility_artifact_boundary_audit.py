from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.common import ROOT, ensure_parent_dir, resolve_repo_path
from src.handoff_zip_export import is_forbidden_entry as is_handoff_forbidden_entry

DEFAULT_CSV_OUTPUT = "data/processed/data_visibility_artifact_boundary_audit.csv"
DEFAULT_JSON_OUTPUT = "data/processed/data_visibility_artifact_boundary_audit.json"
DEFAULT_REPORT_TEMPLATE = "reports/{as_of_date}/data_visibility_artifact_boundary_audit.md"

FIELDNAMES = [
    "path",
    "exists",
    "gitignore_status",
    "gitignore_rule_source",
    "repo_tracking_intent",
    "handoff_visibility",
    "reproduction_classification",
    "data_source_registry_relation",
    "privacy_risk_if_tracked",
    "decision_risk_if_ignored",
    "project_level_impact",
    "recommended_action",
    "requires_operator_review",
    "notes",
]

REPRESENTATIVE_PATHS = [
    ".gitignore",
    "README.md",
    "pyproject.toml",
    "docs/governance/CIOS_PRACTICAL_OPERATING_STANDARD.md",
    "docs/architecture/CIOS_FEATURE_STATUS.yaml",
    "docs/architecture/CURRENT_KNOWN_GAPS.md",
    "data/raw/private/example.csv",
    "data/raw/private/fundamentals/personal_fundamentals_snapshot.csv",
    "data/raw/private/fundamentals/personal_fundamentals_snapshot_review.csv",
    "data/raw/personal_positions_snapshot.csv",
    "data/raw/personal_fundamentals_master.csv",
    "data/raw/personal_fundamentals_master_template.csv",
    "data/raw/personal_fundamentals_evidence.csv",
    "data/raw/personal_fundamentals_evidence_template.csv",
    "data/raw/personal_fundamentals_overlay.csv",
    "data/raw/personal_sec_identity_map.csv",
    "data/raw/personal_sec_identity_map_template.csv",
    "data/raw/sample_watchlist.csv",
    "data/raw/sample_cost_tax_ledger.csv",
    "data/processed/personal_monthly_buy_ranking.csv",
    "data/processed/rebalance_proposals.csv",
    "data/processed/decision_quality_state.json",
    "data/processed/decision_quality_state.csv",
    "data/processed/data_freshness_summary.json",
    "data/processed/review_queue_summary.json",
    "data/processed/personal_run_manifest.json",
    "data/processed/personal_run_used_inputs.csv",
    "data/processed/personal_cash_refill_review.csv",
    "data/processed/personal_rebalance_review.csv",
    "data/processed/monthly_portfolio_decision_brief.json",
    "data/processed/monthly_portfolio_decision_brief.csv",
    "data/processed/ranking_robustness_sensitivity.json",
    "data/processed/ranking_robustness_sensitivity.csv",
    "data/processed/gitignore_artifact_boundary_audit.csv",
    "data/processed/data_visibility_artifact_boundary_audit.csv",
    "reports/2026-05-30/personal_run_report.md",
    "reports/2026-05-30/personal_monthly_decision_report.md",
    "reports/2026-05-30/decision_quality_report.md",
    "reports/2026-05-30/data_freshness_summary.md",
    "reports/2026-05-30/monthly_portfolio_decision_brief.md",
    "reports/2026-05-30/ranking_robustness_sensitivity_report.md",
    "reports/examples/monthly_portfolio_decision_brief_example.md",
    "external_review_packet/00_READ_ME_FIRST.md",
    "external_review_packet/HANDOFF_LATEST_CONTEXT.md",
    "external_review_packet/HANDOFF_LATEST.sha256",
    "external_review_packet/HANDOFF_LATEST.zip",
    "outputs/handoffs/latest/HANDOFF_LATEST.zip",
    "outputs/handoffs/latest/HANDOFF_LATEST.sha256",
    "outputs/reports/local_validation.log",
    "_local_handoff_archive/example.zip",
    "strategy/README.md",
    "strategy/templates/example_strategy.md",
    "strategy/private/current_strategy.md",
    "strategy/current_portfolio_thesis.md",
    ".env",
    ".env.local",
    "website/app/.env.local",
    "sec_user_agent.local.txt",
    "node_modules/example.js",
    "website/compound-income-os-landing/dist/index.html",
    "website/compound-income-os-landing/playwright-report/index.html",
    "tests/_tmp_rules.yaml",
    "__pycache__/example.pyc",
]


@dataclass(frozen=True)
class AuditRow:
    path: str
    exists: str
    gitignore_status: str
    gitignore_rule_source: str
    repo_tracking_intent: str
    handoff_visibility: str
    reproduction_classification: str
    data_source_registry_relation: str
    privacy_risk_if_tracked: str
    decision_risk_if_ignored: str
    project_level_impact: str
    recommended_action: str
    requires_operator_review: str
    notes: str


@dataclass(frozen=True)
class GitBoundaryContext:
    tracked_paths: frozenset[str]
    ignored_rules: dict[str, str]


def normalize_path(path_value: str | Path) -> str:
    return str(path_value).replace("\\", "/").lstrip("/")


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True, check=False)


def build_git_context(repo_root: Path, paths: list[str]) -> GitBoundaryContext:
    tracked_result = _run_git(repo_root, ["ls-files"])
    tracked_paths = frozenset(normalize_path(line) for line in tracked_result.stdout.splitlines() if line.strip())
    ignored_rules: dict[str, str] = {}
    untracked = [path for path in paths if path not in tracked_paths]
    if untracked:
        result = subprocess.run(
            ["git", "check-ignore", "-v", "--stdin"],
            cwd=repo_root,
            input="\n".join(untracked) + "\n",
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode in {0, 1}:
            for line in result.stdout.splitlines():
                ignored_path = normalize_path(line.rsplit("\t", 1)[-1])
                ignored_rules[ignored_path] = line
    return GitBoundaryContext(tracked_paths=tracked_paths, ignored_rules=ignored_rules)


def gitignore_rule(context: GitBoundaryContext, rel_path: str) -> tuple[str, str]:
    if rel_path in context.tracked_paths:
        return "TRACKED_OR_TRACKABLE", "TRACKED_BY_GIT"
    if rel_path in context.ignored_rules:
        return "IGNORED", context.ignored_rules[rel_path]
    return "TRACKED_OR_TRACKABLE", "NO_MATCHING_IGNORE_RULE"


def load_data_source_paths(repo_root: Path) -> dict[str, str]:
    config_path = repo_root / "configs" / "personal_run_data_sources.yaml"
    if not config_path.is_file():
        return {}
    data = json.loads(config_path.read_text(encoding="utf-8"))
    sources = data.get("sources", {})
    result: dict[str, str] = {}
    if not isinstance(sources, dict):
        return result
    for entry in sources.values():
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            result[normalize_path(entry["path"])] = _registry_relation(entry)
    return result


def _registry_relation(entry: dict[str, Any]) -> str:
    enabled = bool(entry.get("enabled"))
    required = bool(entry.get("required"))
    if not enabled:
        return "CONFIGURED_DISABLED"
    if required:
        return "CONFIGURED_REQUIRED"
    return "CONFIGURED_OPTIONAL"


def classify_row(repo_root: Path, rel_path: str, registry_paths: dict[str, str], git_context: GitBoundaryContext) -> AuditRow:
    path = normalize_path(rel_path)
    exists = str((repo_root / path).exists()).lower()
    gitignore_status, rule_source = gitignore_rule(git_context, path)
    intent = repo_tracking_intent(path)
    handoff = handoff_visibility(path)
    reproduction = reproduction_classification(path)
    registry_relation = data_source_registry_relation(path, registry_paths)
    privacy_risk = privacy_risk_if_tracked(path)
    decision_risk = decision_risk_if_ignored(path)
    impact = project_level_impact(path, intent, handoff, registry_relation)
    action = recommended_action(path, intent, impact)
    operator_review = str(action in {"OPERATOR_REVIEW_REQUIRED", "ADD_DOC_BOUNDARY", "TRACK_TEMPLATE_ONLY", "TRACK_SANITIZED_EXAMPLE_ONLY"}).lower()
    return AuditRow(
        path=path,
        exists=exists,
        gitignore_status=gitignore_status,
        gitignore_rule_source=rule_source,
        repo_tracking_intent=intent,
        handoff_visibility=handoff,
        reproduction_classification=reproduction,
        data_source_registry_relation=registry_relation,
        privacy_risk_if_tracked=privacy_risk,
        decision_risk_if_ignored=decision_risk,
        project_level_impact=impact,
        recommended_action=action,
        requires_operator_review=operator_review,
        notes=notes_for(path),
    )


def repo_tracking_intent(path: str) -> str:
    if path in {".gitignore", "README.md", "pyproject.toml"}:
        return "TRACKED_SOURCE" if path == "README.md" else "TRACKED_CONFIG"
    if path.startswith("docs/"):
        return "TRACKED_DOC"
    if path.startswith("tests/") and not path.startswith("tests/_tmp"):
        return "TRACKED_TEST"
    if path.startswith("configs/"):
        return "TRACKED_CONFIG"
    if path.startswith("external_review_packet/") and not path.endswith(".zip"):
        return "REVIEW_PACKET_ONLY"
    if path == "external_review_packet/HANDOFF_LATEST.zip":
        return "REVIEW_PACKET_ONLY"
    if path.endswith((".zip", ".log", ".pyc")) or "node_modules/" in path or "/dist/" in path or "playwright-report/" in path:
        return "SHOULD_NOT_EXIST_IN_REPO"
    if path.endswith("_template.csv") or "/templates/" in path:
        return "TRACKED_TEMPLATE"
    if "example" in path and not path.startswith(("data/raw/private/", "outputs/", "_local_handoff_archive/")):
        return "TRACKED_SANITIZED_EXAMPLE"
    if path.startswith(("data/raw/private/", "strategy/private/")) or path in {".env", ".env.local", "website/app/.env.local", "sec_user_agent.local.txt"}:
        return "PRIVATE_LOCAL_ONLY"
    if path.startswith("data/raw/personal_") and not path.endswith("_template.csv"):
        return "PRIVATE_LOCAL_ONLY"
    if path.startswith(("data/processed/", "reports/", "outputs/")):
        return "GENERATED_LOCAL_ONLY"
    if path.startswith("strategy/"):
        return "PRIVATE_LOCAL_ONLY"
    return "UNKNOWN"


def handoff_visibility(path: str) -> str:
    if path.startswith("external_review_packet/") and not path.endswith(".zip"):
        return "REVIEW_PACKET_METADATA"
    if path == "external_review_packet/HANDOFF_LATEST.zip":
        return "REVIEW_PACKET_METADATA"
    if is_handoff_forbidden_entry(path):
        if path.startswith("data/raw/private/") or path.startswith("data/raw/personal_") or path.startswith("strategy/private/"):
            return "OMITTED_PRIVATE"
        return "FORBIDDEN"
    if path.startswith(("docs/", "src/", "tests/", "configs/")) or path in {"README.md", ".gitignore", "pyproject.toml"}:
        return "INCLUDED_BY_DEFAULT"
    if path.startswith(("data/processed/", "reports/")):
        return "INCLUDED_IF_ALLOWLISTED"
    return "NOT_SELECTED_FOR_PROFILE"


def reproduction_classification(path: str) -> str:
    if path.startswith(("docs/", "src/", "tests/", "configs/")) or path in {"README.md", ".gitignore", "pyproject.toml"}:
        return "ZIP_SAFE"
    if path.startswith("data/raw/private/") or path.startswith("strategy/private/"):
        return "PRIVATE_INPUT_REQUIRED"
    if path.startswith("data/raw/personal_") and not path.endswith("_template.csv"):
        return "PRIVATE_INPUT_REQUIRED"
    if path.startswith(("external_review_packet/", "outputs/", "_local_handoff_archive/")) or path.endswith((".zip", ".log")):
        return "NOT_APPLICABLE"
    if path.startswith(("data/processed/", "reports/")):
        return "LOCAL_REPO_REQUIRED"
    return "UNKNOWN"


def data_source_registry_relation(path: str, registry_paths: dict[str, str]) -> str:
    if path in registry_paths:
        return registry_paths[path]
    if path.startswith("data/processed/"):
        return "PRODUCED_OUTPUT"
    if path.startswith(("docs/", "src/", "tests/", "external_review_packet/", "outputs/", "reports/", "strategy/")):
        return "NOT_APPLICABLE"
    if path.startswith("data/raw/"):
        return "NOT_REGISTERED"
    return "UNKNOWN"


def privacy_risk_if_tracked(path: str) -> str:
    if path in {".env", ".env.local", "website/app/.env.local", "sec_user_agent.local.txt"}:
        return "CRITICAL"
    if path.startswith(("data/raw/private/", "strategy/private/")):
        return "CRITICAL"
    if path.startswith("data/raw/personal_") and not path.endswith("_template.csv"):
        return "HIGH"
    if path.startswith("reports/") and "/personal_" in path:
        return "HIGH"
    if path.startswith("data/processed/personal_"):
        return "MEDIUM"
    if path.startswith("strategy/") and not path.startswith("strategy/templates/"):
        return "HIGH"
    if path.startswith(("outputs/", "_local_handoff_archive/")) or path.endswith((".zip", ".log")):
        return "MEDIUM"
    return "NONE"


def decision_risk_if_ignored(path: str) -> str:
    if "monthly_portfolio_decision_brief" in path:
        return "HIGH"
    if "ranking_robustness_sensitivity" in path:
        return "MEDIUM"
    if path in {
        "data/processed/decision_quality_state.json",
        "data/processed/data_freshness_summary.json",
        "data/processed/review_queue_summary.json",
        "data/processed/personal_run_manifest.json",
        "data/processed/personal_run_used_inputs.csv",
    }:
        return "MEDIUM"
    if path.endswith("_template.csv") or path.startswith("docs/"):
        return "LOW"
    return "NONE"


def project_level_impact(path: str, intent: str, handoff: str, registry_relation: str) -> str:
    if path.startswith(("data/raw/private/", "strategy/private/")) or path in {".env", ".env.local", "website/app/.env.local", "sec_user_agent.local.txt"}:
        return "PRIVACY_PROTECTION"
    if "monthly_portfolio_decision_brief" in path:
        return "FUTURE_PATCH_PRECONDITION"
    if "ranking_robustness_sensitivity" in path:
        return "FUTURE_PATCH_PRECONDITION"
    if path.startswith("data/processed/") or path.startswith("reports/"):
        return "REVIEWABILITY_GAP"
    if path.startswith("external_review_packet/"):
        return "SAFE_CURRENT_BOUNDARY" if handoff == "REVIEW_PACKET_METADATA" else "HANDOFF_VISIBILITY_GAP"
    if registry_relation in {"CONFIGURED_REQUIRED", "CONFIGURED_OPTIONAL", "CONFIGURED_DISABLED"}:
        return "SAFE_CURRENT_BOUNDARY"
    if intent in {"TRACKED_SOURCE", "TRACKED_CONFIG", "TRACKED_TEST", "TRACKED_DOC", "TRACKED_TEMPLATE", "TRACKED_SANITIZED_EXAMPLE"}:
        return "SAFE_CURRENT_BOUNDARY"
    if path.startswith(("outputs/", "_local_handoff_archive/")):
        return "SOURCE_OF_TRUTH_AMBIGUITY"
    return "REPRODUCIBILITY_GAP"


def recommended_action(path: str, intent: str, impact: str) -> str:
    if impact == "PRIVACY_PROTECTION":
        return "KEEP_IGNORED"
    if intent == "SHOULD_NOT_EXIST_IN_REPO":
        return "ADD_TO_OMITTED_ARTIFACT_REGISTER"
    if intent in {"TRACKED_SOURCE", "TRACKED_CONFIG", "TRACKED_TEST", "TRACKED_DOC"}:
        return "KEEP_TRACKED"
    if intent == "TRACKED_TEMPLATE":
        return "TRACK_TEMPLATE_ONLY"
    if intent == "TRACKED_SANITIZED_EXAMPLE":
        return "TRACK_SANITIZED_EXAMPLE_ONLY"
    if "monthly_portfolio_decision_brief" in path or "ranking_robustness_sensitivity" in path:
        return "ADD_DOC_BOUNDARY"
    if path.startswith(("data/processed/", "reports/")):
        return "ADD_MANIFEST_OR_HASH_ONLY"
    if path.startswith(("outputs/", "_local_handoff_archive/")) or path.endswith((".zip", ".log")):
        return "ADD_TO_OMITTED_ARTIFACT_REGISTER"
    return "NO_CHANGE"


def notes_for(path: str) -> str:
    if "monthly_portfolio_decision_brief" in path:
        return "Future operational decision artifact; prefer schema/template/sanitized example plus manifest or hash before tracking real outputs."
    if "ranking_robustness_sensitivity" in path:
        return "Future review-relevant robustness artifact; not automatically safe to commit with real portfolio context."
    if path.startswith("data/raw/private/"):
        return "Private raw path; contents must not be read by this audit."
    if path.startswith("external_review_packet/"):
        return "Central reviewer-facing handoff boundary."
    if path.startswith("outputs/"):
        return "Generated local evidence; not authoritative external handoff."
    if path.startswith("strategy/private/"):
        return "Private strategy path; keep local-only."
    return ""


def build_audit_rows(repo_root: str | Path = ROOT) -> list[AuditRow]:
    root = resolve_repo_path(repo_root)
    registry_paths = load_data_source_paths(root)
    paths = [normalize_path(path) for path in REPRESENTATIVE_PATHS]
    git_context = build_git_context(root, paths)
    return [classify_row(root, path, registry_paths, git_context) for path in paths]


def _serializable_rows(rows: list[AuditRow]) -> list[dict[str, str]]:
    return [asdict(row) for row in rows]


def write_csv(path_value: str | Path, rows: list[AuditRow]) -> Path:
    path = ensure_parent_dir(path_value)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        for row in _serializable_rows(rows):
            writer.writerow(row)
    return path


def write_json(path_value: str | Path, rows: list[AuditRow]) -> Path:
    path = ensure_parent_dir(path_value)
    path.write_text(json.dumps(_serializable_rows(rows), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def build_markdown_report(rows: list[AuditRow], *, as_of_date: str) -> str:
    impacts = _count_by(rows, "project_level_impact")
    actions = _count_by(rows, "recommended_action")
    critical = [row for row in rows if row.privacy_risk_if_tracked == "CRITICAL"]
    future = [row for row in rows if row.project_level_impact == "FUTURE_PATCH_PRECONDITION"]
    review_gaps = [row for row in rows if row.project_level_impact == "REVIEWABILITY_GAP"]
    reproduction_gaps = [row for row in rows if row.project_level_impact == "REPRODUCIBILITY_GAP"]

    return (
        "# Data Visibility And Artifact Boundary Audit\n\n"
        f"- as_of_date: `{as_of_date}`\n"
        f"- representative_path_count: `{len(rows)}`\n\n"
        "## Executive Summary\n\n"
        "The current CIOS boundary model protects private/raw/provider/broker-like artifacts by default, "
        "while generated portfolio-decision outputs remain local-only unless represented by sanitized examples, "
        "templates, manifests, hashes or omitted-artifact records.\n\n"
        "## Current Boundary Model\n\n"
        "- Git/.gitignore keeps generated `data/processed/`, `reports/`, `outputs/`, private raw inputs and strategy content local by default.\n"
        "- The handoff exporter forbids private raw paths, `.env`, user-agent files, ZIP/log/cache/build artifacts and local output folders.\n"
        "- The central `external_review_packet/` is reviewer-facing metadata/evidence, not source truth by itself.\n"
        "- The reproduction matrix separates ZIP-safe, local-repo-required, private-input-required and optional-tooling checks.\n"
        "- The data-source registry exposes configured required/optional/disabled local sources without publishing private contents.\n\n"
        "## Critical Blockers\n\n"
        + _bullet_paths(critical, "No critical privacy path should be tracked or included in external handoff.")
        + "\n## Privacy Protections That Must Remain\n\n"
        "Private raw, personal raw, private strategy, `.env`, user-agent, ZIP, log, cache, node_modules and build artifacts must remain excluded unless a later Human Operator-approved boundary says otherwise.\n\n"
        "## Reviewability Gaps\n\n"
        + _bullet_paths(review_gaps, "Generated outputs need manifest/hash/status representation before they become review evidence.")
        + "\n## Reproduction Gaps\n\n"
        + _bullet_paths(reproduction_gaps, "Some representative paths are not registered as ZIP-safe review evidence.")
        + "\n## Future Portfolio-Decision Artifact Implications\n\n"
        + _bullet_paths(future, "Future operational decision outputs require explicit boundary decisions before MVP work.")
        + "\n## Recommended Next Patch Impact\n\n"
        "MONTHLY_PORTFOLIO_DECISION_BRIEF_MVP is not blocked by privacy boundaries, but it should define output treatment before writing real operator reports: generated local outputs by default, sanitized examples or templates for review, and manifest/hash/status rows for auditability.\n\n"
        "RANKING_ROBUSTNESS_SENSITIVITY_PRODUCER_MVP should produce review-relevant artifacts without committing real personal decision context by default.\n\n"
        "## Impact Counts\n\n"
        + _format_counts(impacts)
        + "\n## Recommended Action Counts\n\n"
        + _format_counts(actions)
        + "\n## Explicit Non-Claims\n\n"
        "This audit does not implement broker import, provider/API integration, order execution, buy/sell automation, replay, backtesting, outcome attribution, valuation automation, scoring formula changes, ranking formula changes, portfolio-rule changes, runtime enforcement, production readiness or investment readiness.\n"
    )


def _count_by(rows: list[AuditRow], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(getattr(row, field))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _format_counts(counts: dict[str, int]) -> str:
    return "".join(f"- `{key}`: `{value}`\n" for key, value in counts.items())


def _bullet_paths(rows: list[AuditRow], fallback: str) -> str:
    if not rows:
        return f"- {fallback}\n"
    return "".join(f"- `{row.path}`: {row.notes or row.recommended_action}\n" for row in rows[:12])


def write_markdown(path_value: str | Path, rows: list[AuditRow], *, as_of_date: str) -> Path:
    path = ensure_parent_dir(path_value)
    path.write_text(build_markdown_report(rows, as_of_date=as_of_date), encoding="utf-8")
    return path


def run_audit(
    *,
    repo_root: str | Path = ROOT,
    as_of_date: str,
    out_csv: str | Path = DEFAULT_CSV_OUTPUT,
    out_json: str | Path = DEFAULT_JSON_OUTPUT,
    report: str | Path | None = None,
) -> dict[str, Path]:
    rows = build_audit_rows(repo_root)
    report_path = report or DEFAULT_REPORT_TEMPLATE.format(as_of_date=as_of_date)
    return {
        "csv": write_csv(out_csv, rows),
        "json": write_json(out_json, rows),
        "report": write_markdown(report_path, rows, as_of_date=as_of_date),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit CIOS data visibility and artifact boundaries.")
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--out-csv", default=DEFAULT_CSV_OUTPUT)
    parser.add_argument("--out-json", default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--report", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = run_audit(
        repo_root=args.repo_root,
        as_of_date=args.as_of_date,
        out_csv=args.out_csv,
        out_json=args.out_json,
        report=args.report,
    )
    for key, path in outputs.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
