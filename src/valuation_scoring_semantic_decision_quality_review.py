from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from src.common import resolve_repo_path, write_csv_rows

DEFAULT_ARTIFACTS = [
    "docs/contracts/VALUATION_ENGINE_BOUNDARY_CONTRACT.md",
    "src/valuation_engine.py",
    "src/scoring_engine.py",
    "src/monthly_ranking_engine.py",
    "src/build_monthly_decision_report.py",
    "src/personal_decision_quality_state.py",
]
DEFAULT_OUTPUT_CSV = "data/processed/valuation_scoring_semantic_decision_quality_review.csv"
DEFAULT_OUTPUT_JSON = "data/processed/valuation_scoring_semantic_decision_quality_review.json"

CSV_FIELDS = [
    "check_id",
    "as_of_date",
    "artifact_path",
    "reviewed_surface",
    "reviewed_term",
    "semantic_category",
    "severity",
    "status",
    "evidence_snippet",
    "risk_description",
    "expected_operator_interpretation",
    "recommended_follow_up",
    "non_scope_confirmation",
]
SUMMARY_FIELDS = ["metric", "value"]
NON_SCOPE_CONFIRMATION = (
    "read-only evidence; no valuation automation; no formula change; no ranking change; "
    "no buy/sell automation; no investment advice; Human Operator remains final authority"
)
UNCERTAINTY_TERMS = ("MISSING", "MISSING_DATA", "REVIEW", "STALE", "CONFLICT", "UNKNOWN", "BLOCKED", "INVALID")
FORBIDDEN_ACTION_PATTERNS = [
    r"\bexecute\s+order\b",
    r"\bplace\s+order\b",
    r"\bautomatically\s+buy\b",
    r"\bautomatically\s+sell\b",
    r"\bbuy\s+now\b",
    r"\bsell\s+now\b",
    r"\bmust\s+buy\b",
    r"\bmust\s+sell\b",
    r"\bguaranteed\b",
    r"\brisk[- ]free\b",
]
MALFORMED_NUMERIC_PATTERNS = [
    (r"\bN/A\b", "placeholder numeric text"),
    (r"(?<!\w)--(?!\w)", "dash placeholder numeric text"),
    (r"\bnot-a-number\b", "explicit non-numeric text"),
    (r"\b\d+(?:\.\d+)?%", "percentage-formatted numeric text"),
    (r"\b\d+,\d+\b", "locale-formatted numeric text"),
]


@dataclass(frozen=True)
class SemanticRule:
    term: str
    reviewed_surface: str
    semantic_category: str
    severity: str
    status: str
    risk_description: str
    expected_operator_interpretation: str
    recommended_follow_up: str
    case_sensitive: bool = False


@dataclass(frozen=True)
class ValuationScoringSemanticDecisionQualityReviewResult:
    csv_output: Path
    json_output: Path
    report_output: Path
    rows: list[dict[str, str]]
    summary: dict[str, str]


RULES = [
    SemanticRule(
        "BUYABLE",
        "purchase_state label",
        "AUTOMATION_RISK",
        "P1",
        "REVIEW",
        "The label can be misread as order readiness if detached from portfolio and operator boundaries.",
        "Treat as a deterministic review label only, not an instruction to trade.",
        "Consider operator wording that says reviewable candidate rather than executable order.",
    ),
    SemanticRule(
        "eligible_for_purchase",
        "purchase eligibility boolean",
        "AUTOMATION_RISK",
        "P1",
        "REVIEW",
        "A boolean eligibility field can be misread as automatic approval.",
        "Treat as local scoring evidence only; Human Operator decides.",
        "Keep explicit no-order and no-auto-acceptance wording near consumer surfaces.",
    ),
    SemanticRule(
        "TOO_EXPENSIVE",
        "purchase_state label",
        "LABEL_AMBIGUITY",
        "P2",
        "WARNING",
        "The label compresses a valuation window into a categorical phrase.",
        "Treat as a threshold explanation, not a complete valuation conclusion.",
        "Keep valuation thresholds and data-quality caveats visible.",
    ),
    SemanticRule(
        "BLOCKED",
        "purchase_state label",
        "FAILURE_MODE_VISIBILITY",
        "P2",
        "WARNING",
        "Blocking language is useful but must show the underlying reason.",
        "Treat as a guardrail/review state, not runtime enforcement.",
        "Ensure reason codes stay visible on report surfaces.",
    ),
    SemanticRule(
        "fair_value_estimate",
        "valuation field",
        "CERTAINTY_RISK",
        "P2",
        "WARNING",
        "The field can look more precise than the current heuristic supports.",
        "Treat as a heuristic estimate from provided inputs.",
        "Keep boundary wording that this is not valuation automation or advice.",
    ),
    SemanticRule(
        "margin_of_safety_pct",
        "valuation field",
        "CERTAINTY_RISK",
        "P2",
        "WARNING",
        "The field can imply valuation confidence if missing/stale inputs are hidden.",
        "Treat as a diagnostic percentage, not a guarantee.",
        "Keep data-quality and provenance flags adjacent in operator surfaces.",
    ),
    SemanticRule(
        "fair_value_score",
        "valuation score field",
        "CERTAINTY_RISK",
        "P2",
        "WARNING",
        "A numeric valuation score can mask fallback or degraded data.",
        "Treat as bounded scoring evidence only.",
        "Keep fallback and data-quality semantics visible.",
    ),
    SemanticRule(
        "valuation_score",
        "scoring field",
        "CERTAINTY_RISK",
        "P2",
        "WARNING",
        "A valuation score can be overinterpreted as investment readiness.",
        "Treat as one scoring component, not a decision.",
        "Keep formula and non-advice boundaries documented.",
    ),
    SemanticRule(
        "valuation_comment",
        "operator-facing comment field",
        "LABEL_AMBIGUITY",
        "P2",
        "REVIEW",
        "Valuation comments are operator-facing and may carry advice-like wording.",
        "Treat as explanation text that requires boundary wording.",
        "Review report wording before future operator-surface expansion.",
    ),
    SemanticRule(
        "hybride Fair-Value-Sicht",
        "valuation comment",
        "CERTAINTY_RISK",
        "P2",
        "REVIEW",
        "Hybrid fair-value wording can imply methodology maturity.",
        "Treat as current heuristic wording only.",
        "Define a later methodology contract before broadening this language.",
    ),
    SemanticRule(
        "hybrid Fair Value",
        "valuation comment",
        "CERTAINTY_RISK",
        "P2",
        "REVIEW",
        "Hybrid fair-value wording can imply methodology maturity.",
        "Treat as current heuristic wording only.",
        "Define a later methodology contract before broadening this language.",
    ),
    SemanticRule(
        "Unterbewertung",
        "valuation comment",
        "ADVICE_RISK",
        "P1",
        "REVIEW",
        "Undervaluation wording can be misread as an investment conclusion.",
        "Treat as heuristic valuation evidence, not investment advice.",
        "Consider softer wording or adjacent no-advice boundary text.",
    ),
    SemanticRule(
        "estimated fair value",
        "valuation comment",
        "CERTAINTY_RISK",
        "P2",
        "WARNING",
        "Estimated fair-value wording needs visible uncertainty boundaries.",
        "Treat as estimate only.",
        "Keep missing/stale/conflict flags near the estimate.",
    ),
    SemanticRule(
        "geschaetzten Fair Value",
        "valuation comment",
        "CERTAINTY_RISK",
        "P2",
        "WARNING",
        "Estimated fair-value wording needs visible uncertainty boundaries.",
        "Treat as estimate only.",
        "Keep missing/stale/conflict flags near the estimate.",
    ),
    SemanticRule(
        "decision_confidence_level",
        "decision-quality field",
        "OPERATOR_BOUNDARY",
        "P2",
        "WARNING",
        "Confidence language can be mistaken for investment confidence.",
        "Treat as process/review confidence only.",
        "Keep explicit text that this is not investment confidence or order readiness.",
    ),
    SemanticRule(
        "review_required",
        "decision-quality field",
        "FAILURE_MODE_VISIBILITY",
        "INFO",
        "OK",
        "Review-required fields support uncertainty visibility.",
        "Treat as operator review evidence.",
        "Keep the field visible in downstream reports.",
    ),
]


def default_report_output(as_of_date: str) -> str:
    return f"reports/{as_of_date}/valuation_scoring_semantic_decision_quality_review.md"


def repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<outside_repo>"


def evidence_snippet(text: str, start: int, end: int, width: int = 80) -> str:
    left = max(0, start - width // 2)
    right = min(len(text), end + width // 2)
    snippet = re.sub(r"\s+", " ", text[left:right]).strip()
    return snippet[:160]


def rule_matches(text: str, rule: SemanticRule) -> list[tuple[int, int]]:
    flags = 0 if rule.case_sensitive else re.IGNORECASE
    return [(match.start(), match.end()) for match in re.finditer(re.escape(rule.term), text, flags)]


def make_row(
    *,
    check_id: str,
    as_of_date: str,
    artifact_path: str,
    reviewed_surface: str,
    reviewed_term: str,
    semantic_category: str,
    severity: str,
    status: str,
    evidence: str,
    risk_description: str,
    expected_operator_interpretation: str,
    recommended_follow_up: str,
) -> dict[str, str]:
    return {
        "check_id": check_id,
        "as_of_date": as_of_date,
        "artifact_path": artifact_path,
        "reviewed_surface": reviewed_surface,
        "reviewed_term": reviewed_term,
        "semantic_category": semantic_category,
        "severity": severity,
        "status": status,
        "evidence_snippet": evidence,
        "risk_description": risk_description,
        "expected_operator_interpretation": expected_operator_interpretation,
        "recommended_follow_up": recommended_follow_up,
        "non_scope_confirmation": NON_SCOPE_CONFIRMATION,
    }


def forbidden_action_rows(text: str, *, as_of_date: str, artifact_path: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for pattern in FORBIDDEN_ACTION_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            rows.append(
                make_row(
                    check_id=f"FORBIDDEN_ACTION_WORDING::{artifact_path}::{pattern}",
                    as_of_date=as_of_date,
                    artifact_path=artifact_path,
                    reviewed_surface="operator/action wording",
                    reviewed_term=pattern,
                    semantic_category="ADVICE_RISK",
                    severity="P0",
                    status="FAIL",
                    evidence=evidence_snippet(text, match.start(), match.end()),
                    risk_description="The wording can imply order execution, guaranteed outcome or automatic action.",
                    expected_operator_interpretation="No source text may instruct or imply automated order action.",
                    recommended_follow_up="Replace action-implying wording with review-only evidence language.",
                )
            )
    return rows


def malformed_numeric_rows(text: str, *, as_of_date: str, artifact_path: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for pattern, label in MALFORMED_NUMERIC_PATTERNS:
        for index, match in enumerate(re.finditer(pattern, text, re.IGNORECASE), start=1):
            rows.append(
                make_row(
                    check_id=f"MALFORMED_NUMERIC_SURFACE::{artifact_path}::{label}::{index}",
                    as_of_date=as_of_date,
                    artifact_path=artifact_path,
                    reviewed_surface="valuation/scoring input wording",
                    reviewed_term=label,
                    semantic_category="DATA_QUALITY_MASKING",
                    severity="P2",
                    status="REVIEW",
                    evidence=evidence_snippet(text, match.start(), match.end()),
                    risk_description="Malformed or locale-formatted numeric-looking input can mask fallback valuation/scoring behavior.",
                    expected_operator_interpretation="Malformed numeric inputs must remain review evidence and must not imply confident valuation precision.",
                    recommended_follow_up="Keep malformed numeric values visible as review/failure-mode evidence; do not silently impute.",
                )
            )
    return rows


def failure_mode_term_rows(text: str, *, as_of_date: str, artifact_path: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for term in UNCERTAINTY_TERMS:
        for index, match in enumerate(re.finditer(re.escape(term), text, re.IGNORECASE), start=1):
            context = evidence_snippet(text, match.start(), match.end())
            has_explanation = bool(re.search(r"\b(reason|because|requires|visible|review|missing|stale|conflict|unknown|invalid|blocked|not silent|no imputation)\b", context, re.IGNORECASE))
            rows.append(
                make_row(
                    check_id=f"FAILURE_MODE_TERM::{artifact_path}::{term}::{index}",
                    as_of_date=as_of_date,
                    artifact_path=artifact_path,
                    reviewed_surface="failure-mode state",
                    reviewed_term=term,
                    semantic_category="FAILURE_MODE_VISIBILITY",
                    severity="INFO" if has_explanation else "P2",
                    status="OK" if has_explanation else "WARNING",
                    evidence=context,
                    risk_description=(
                        "Failure-mode state is visible with explanatory context."
                        if has_explanation
                        else "Failure-mode state is visible but lacks enough adjacent explanatory context."
                    ),
                    expected_operator_interpretation="Missing, stale, conflict, unknown, invalid, review and blocked states must remain visible.",
                    recommended_follow_up=(
                        "Maintain adjacent reason/boundary wording."
                        if has_explanation
                        else "Add adjacent reason or operator-boundary wording before relying on this surface."
                    ),
                )
            )
    return rows


def uncertainty_visibility_row(text: str, *, as_of_date: str, artifact_path: str, found_relevant_term: bool) -> dict[str, str]:
    has_uncertainty = any(term.lower() in text.lower() for term in UNCERTAINTY_TERMS)
    if found_relevant_term and not has_uncertainty:
        status = "REVIEW"
        severity = "P1"
        risk = "Relevant valuation/scoring wording exists without visible missing/review/stale/conflict language."
        follow_up = "Keep uncertainty and degraded-data states visible near positive scoring language."
    elif found_relevant_term:
        status = "OK"
        severity = "INFO"
        risk = "Relevant valuation/scoring wording coexists with visible uncertainty/review state language."
        follow_up = "Maintain this visibility in future operator surfaces."
    else:
        status = "NOT_APPLICABLE"
        severity = "INFO"
        risk = "No relevant valuation/scoring term was detected in this artifact."
        follow_up = "No semantic follow-up for this artifact."
    return make_row(
        check_id=f"FAILURE_MODE_VISIBILITY::{artifact_path}",
        as_of_date=as_of_date,
        artifact_path=artifact_path,
        reviewed_surface="failure-mode visibility",
        reviewed_term="missing/stale/conflict/review visibility",
        semantic_category="FAILURE_MODE_VISIBILITY",
        severity=severity,
        status=status,
        evidence=";".join(term for term in UNCERTAINTY_TERMS if term.lower() in text.lower()) or "",
        risk_description=risk,
        expected_operator_interpretation="Positive valuation or scoring wording must not hide missing, stale, conflict or review states.",
        recommended_follow_up=follow_up,
    )


def non_scope_alignment_row(text: str, *, as_of_date: str, artifact_path: str) -> dict[str, str]:
    lowered = text.lower()
    required = ["investment advice", "order execution", "valuation automation"]
    present = [item for item in required if item in lowered]
    status = "OK" if len(present) == len(required) else "REVIEW"
    severity = "INFO" if status == "OK" else "P2"
    return make_row(
        check_id=f"NON_SCOPE_ALIGNMENT::{artifact_path}",
        as_of_date=as_of_date,
        artifact_path=artifact_path,
        reviewed_surface="non-scope wording",
        reviewed_term="investment advice/order execution/valuation automation",
        semantic_category="NON_SCOPE_ALIGNMENT",
        severity=severity,
        status=status,
        evidence=";".join(present),
        risk_description="Non-scope wording must remain explicit where valuation/scoring semantics are documented.",
        expected_operator_interpretation="Review evidence is not investment advice, order execution or valuation automation.",
        recommended_follow_up="Keep explicit non-scope wording in contracts and operator-facing reports.",
    )


def review_text_artifact(path: Path, *, repo_root: Path, as_of_date: str) -> list[dict[str, str]]:
    artifact_path = repo_relative(path, repo_root)
    if not path.exists():
        return [
            make_row(
                check_id=f"INPUT_ARTIFACT_MISSING::{artifact_path}",
                as_of_date=as_of_date,
                artifact_path=artifact_path,
                reviewed_surface="input artifact",
                reviewed_term="missing artifact",
                semantic_category="FAILURE_MODE_VISIBILITY",
                severity="P2",
                status="REVIEW",
                evidence="",
                risk_description="Configured semantic-review input artifact is missing.",
                expected_operator_interpretation="Missing review inputs remain visible and are not silently ignored.",
                recommended_follow_up="Restore the artifact or remove it from the configured review surface.",
            )
        ]
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [
            make_row(
                check_id=f"INPUT_ARTIFACT_UNREADABLE::{artifact_path}",
                as_of_date=as_of_date,
                artifact_path=artifact_path,
                reviewed_surface="input artifact",
                reviewed_term="unreadable artifact",
                semantic_category="FAILURE_MODE_VISIBILITY",
                severity="P2",
                status="REVIEW",
                evidence=str(exc),
                risk_description="Configured semantic-review input artifact could not be read.",
                expected_operator_interpretation="Unreadable review inputs remain visible and are not silently ignored.",
                recommended_follow_up="Fix file readability before relying on semantic-review evidence.",
            )
        ]

    rows: list[dict[str, str]] = []
    found_relevant_term = False
    for rule in RULES:
        matches = rule_matches(text, rule)
        if matches:
            found_relevant_term = True
        for index, (start, end) in enumerate(matches, start=1):
            rows.append(
                make_row(
                    check_id=f"TERM::{artifact_path}::{rule.term}::{index}",
                    as_of_date=as_of_date,
                    artifact_path=artifact_path,
                    reviewed_surface=rule.reviewed_surface,
                    reviewed_term=rule.term,
                    semantic_category=rule.semantic_category,
                    severity=rule.severity,
                    status=rule.status,
                    evidence=evidence_snippet(text, start, end),
                    risk_description=rule.risk_description,
                    expected_operator_interpretation=rule.expected_operator_interpretation,
                    recommended_follow_up=rule.recommended_follow_up,
                )
            )

    rows.extend(forbidden_action_rows(text, as_of_date=as_of_date, artifact_path=artifact_path))
    rows.extend(malformed_numeric_rows(text, as_of_date=as_of_date, artifact_path=artifact_path))
    rows.extend(failure_mode_term_rows(text, as_of_date=as_of_date, artifact_path=artifact_path))
    rows.append(uncertainty_visibility_row(text, as_of_date=as_of_date, artifact_path=artifact_path, found_relevant_term=found_relevant_term))
    if artifact_path.startswith("docs/contracts/"):
        rows.append(non_scope_alignment_row(text, as_of_date=as_of_date, artifact_path=artifact_path))
    if not rows:
        rows.append(
            make_row(
                check_id=f"NO_RELEVANT_TERMS::{artifact_path}",
                as_of_date=as_of_date,
                artifact_path=artifact_path,
                reviewed_surface="semantic scan",
                reviewed_term="none",
                semantic_category="NON_SCOPE_ALIGNMENT",
                severity="INFO",
                status="NOT_APPLICABLE",
                evidence="",
                risk_description="No configured valuation/scoring semantic terms were found.",
                expected_operator_interpretation="No finding for this artifact.",
                recommended_follow_up="No action.",
            )
        )
    return rows


def build_summary(rows: list[dict[str, str]]) -> dict[str, str]:
    statuses = Counter(row["status"] for row in rows)
    severities = Counter(row["severity"] for row in rows)
    highest = "INFO"
    for severity in ("P0", "P1", "P2", "INFO"):
        if severities.get(severity, 0):
            highest = severity
            break
    return {
        "checks_total": str(len(rows)),
        "ok_count": str(statuses.get("OK", 0)),
        "info_count": str(severities.get("INFO", 0)),
        "warning_count": str(statuses.get("WARNING", 0)),
        "review_count": str(statuses.get("REVIEW", 0)),
        "fail_count": str(statuses.get("FAIL", 0)),
        "not_applicable_count": str(statuses.get("NOT_APPLICABLE", 0)),
        "highest_severity": highest,
    }


def render_report(*, as_of_date: str, rows: list[dict[str, str]], summary: dict[str, str]) -> str:
    lines = [
        "# Valuation / Scoring Semantic Decision Quality Review",
        "",
        "## Executive Summary",
        f"- as_of_date: `{as_of_date}`",
        f"- checks_total: `{summary['checks_total']}`",
        f"- OK: `{summary['ok_count']}`",
        f"- WARNING: `{summary['warning_count']}`",
        f"- REVIEW: `{summary['review_count']}`",
        f"- FAIL: `{summary['fail_count']}`",
        f"- NOT_APPLICABLE: `{summary['not_applicable_count']}`",
        f"- highest_severity: `{summary['highest_severity']}`",
        "",
        "## Boundary",
        "- This report is read-only evidence and governance review output.",
        "- Non-scope: no valuation automation; no formula change; no ranking change; no buy/sell automation; no investment advice.",
        "- It does not implement valuation automation, scoring formula changes, ranking changes, buy/sell automation, order execution or investment readiness.",
        "- Human Operator remains final authority and final acceptance authority.",
        "",
        "## Findings",
        "| check_id | artifact | term | category | severity | status | recommended_follow_up |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['check_id']} | {row['artifact_path']} | {row['reviewed_term']} | "
            f"{row['semantic_category']} | {row['severity']} | {row['status']} | {row['recommended_follow_up']} |"
        )
    lines.append("")
    return "\n".join(lines)


def run_valuation_scoring_semantic_decision_quality_review(
    *,
    as_of_date: str,
    repo_root: str | Path = ".",
    artifacts: list[str] | None = None,
    output_csv: str = DEFAULT_OUTPUT_CSV,
    output_json: str = DEFAULT_OUTPUT_JSON,
    report_output: str | None = None,
) -> ValuationScoringSemanticDecisionQualityReviewResult:
    root = resolve_repo_path(repo_root).resolve()
    artifact_paths = artifacts or DEFAULT_ARTIFACTS
    rows: list[dict[str, str]] = []
    for artifact in artifact_paths:
        path = (root / artifact).resolve()
        rows.extend(review_text_artifact(path, repo_root=root, as_of_date=as_of_date))
    rows = sorted(rows, key=lambda row: (row["artifact_path"], row["check_id"], row["reviewed_term"]))
    summary = build_summary(rows)

    csv_path = write_csv_rows(output_csv, CSV_FIELDS, rows)
    json_path = resolve_repo_path(output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(
            {
                "as_of_date": as_of_date,
                "summary": summary,
                "rows": [{field: row[field] for field in CSV_FIELDS} for row in rows],
                "non_scope_confirmation": NON_SCOPE_CONFIRMATION,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    report_target = report_output or default_report_output(as_of_date)
    report_path = resolve_repo_path(report_target)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(as_of_date=as_of_date, rows=rows, summary=summary), encoding="utf-8")
    return ValuationScoringSemanticDecisionQualityReviewResult(
        csv_output=csv_path,
        json_output=json_path,
        report_output=report_path,
        rows=rows,
        summary=summary,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review valuation/scoring semantic decision quality without changing behavior.")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--artifact", action="append", dest="artifacts")
    parser.add_argument("--output-csv", default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output-json", default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--report-output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_valuation_scoring_semantic_decision_quality_review(
        as_of_date=args.as_of_date,
        repo_root=args.repo_root,
        artifacts=args.artifacts,
        output_csv=args.output_csv,
        output_json=args.output_json,
        report_output=args.report_output,
    )
    print(f"csv_output={result.csv_output}")
    print(f"json_output={result.json_output}")
    print(f"report_output={result.report_output}")
    print(f"checks_total={result.summary['checks_total']}")
    print(f"review_count={result.summary['review_count']}")
    print(f"fail_count={result.summary['fail_count']}")
    print(f"highest_severity={result.summary['highest_severity']}")


if __name__ == "__main__":
    main()
