from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
from statistics import NormalDist
from typing import Any, Mapping

from src.canonical_record import verify_hash_chain
from src.common import ensure_parent_dir, load_yaml_config, read_csv_rows, resolve_repo_path
from src.personal_decision_trigger_capture import (
    DECIMAL_FIELDS as TRIGGER_DECIMAL_FIELDS,
    DEFAULT_DECISION_JOURNAL,
    DEFAULT_LEDGER as DEFAULT_TRIGGER_LEDGER,
    DEFAULT_POLICY,
    active_trigger_rows,
    load_trigger_ledger,
)
from src.personal_trigger_resolution import (
    DEFAULT_RESOLUTION_LEDGER,
    load_resolution_ledger,
    validate_resolution_ledger,
)


DEFAULT_SUMMARY_OUTPUT = "data/processed/personal_forward_validation_summary.json"
DEFAULT_REPORT_TEMPLATE = "reports/{as_of_date}/personal_forward_validation_report.md"
BINARY_STATUSES = {"RESOLVED_TRUE", "RESOLVED_FALSE"}


def _parse_date(value: Any, field_name: str) -> date:
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO YYYY-MM-DD") from exc


def _rounded(value: float) -> float:
    return round(value, 6)


def _rate(numerator: int, denominator: int) -> float | None:
    return _rounded(numerator / denominator) if denominator else None


def wilson_interval(
    successes: int,
    n: int,
    *,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    if isinstance(successes, bool) or isinstance(n, bool):
        raise ValueError("successes and n must be integers")
    if not isinstance(successes, int) or not isinstance(n, int):
        raise ValueError("successes and n must be integers")
    if n < 0 or successes < 0 or successes > n:
        raise ValueError("Wilson interval requires 0 <= successes <= n")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1")
    if n == 0:
        return {
            "n": 0,
            "estimate": None,
            "lower_ci": None,
            "upper_ci": None,
            "method": "WILSON",
        }
    z = NormalDist().inv_cdf(0.5 + confidence_level / 2)
    estimate = successes / n
    z_squared = z * z
    denominator = 1 + z_squared / n
    center = (estimate + z_squared / (2 * n)) / denominator
    margin = z * ((estimate * (1 - estimate) / n + z_squared / (4 * n * n)) ** 0.5) / denominator
    return {
        "n": n,
        "estimate": _rounded(estimate),
        "lower_ci": _rounded(max(0.0, center - margin)),
        "upper_ci": _rounded(min(1.0, center + margin)),
        "method": "WILSON",
    }


def _validated_bins(policy_config: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_bins = policy_config.get("calibration_bins")
    if not isinstance(raw_bins, list) or not raw_bins:
        raise ValueError("forward validation policy requires calibration_bins")
    bins: list[dict[str, Any]] = []
    prior_upper: Decimal | None = None
    for index, raw in enumerate(raw_bins):
        if not isinstance(raw, Mapping):
            raise ValueError("each calibration bin must be an object")
        label = str(raw.get("label", "") or "").strip()
        lower = Decimal(str(raw.get("lower", "")))
        upper = Decimal(str(raw.get("upper", "")))
        include_upper = raw.get("include_upper") is True
        if not label or lower < 0 or upper > 1 or lower >= upper:
            raise ValueError(f"invalid calibration bin at index {index}")
        if prior_upper is not None and lower != prior_upper:
            raise ValueError("calibration bins must be contiguous and ordered")
        bins.append(
            {
                "label": label,
                "lower": lower,
                "upper": upper,
                "include_upper": include_upper,
            }
        )
        prior_upper = upper
    if bins[0]["lower"] != 0 or bins[-1]["upper"] != 1 or not bins[-1]["include_upper"]:
        raise ValueError("calibration bins must cover [0,1] and include 1.0")
    if any(item["include_upper"] for item in bins[:-1]):
        raise ValueError("only the final calibration bin may include its upper bound")
    return bins


def _bin_label(probability: Decimal, bins: list[dict[str, Any]]) -> str:
    for item in bins:
        if item["lower"] <= probability < item["upper"]:
            return str(item["label"])
        if item["include_upper"] and probability == item["upper"]:
            return str(item["label"])
    raise ValueError(f"probability is outside configured calibration bins: {probability}")


def _operational_status(decision_count: int, active_trigger_count: int) -> str:
    if decision_count == 0:
        return "READY_FOR_FIRST_REAL_DECISION"
    if active_trigger_count == 0:
        return "READY_FOR_TRIGGER_CAPTURE"
    return "READY_FOR_FORWARD_OBSERVATION"


def build_forward_validation_summary(
    *,
    trigger_rows: list[dict[str, str]],
    resolution_rows: list[dict[str, str]],
    decision_rows: list[dict[str, str]],
    policy_config: Mapping[str, Any],
    as_of_date: str,
) -> dict[str, Any]:
    as_of = _parse_date(as_of_date, "as_of_date")
    if policy_config.get("confirmatory_registration_enabled") is not False:
        raise ValueError("forward validation v1 requires confirmatory_registration_enabled=false")
    bins = _validated_bins(policy_config)

    if trigger_rows:
        verify_hash_chain(trigger_rows, decimal_fields=TRIGGER_DECIMAL_FIELDS)
    elif resolution_rows:
        raise ValueError("resolution ledger cannot contain rows without a trigger ledger")
    if resolution_rows:
        validate_resolution_ledger(resolution_rows, trigger_rows=trigger_rows)

    trigger_by_id = {row["trigger_id"]: row for row in trigger_rows}
    if len(trigger_by_id) != len(trigger_rows):
        raise ValueError("trigger ledger contains duplicate trigger_id values")
    active = active_trigger_rows(trigger_rows)
    resolution_by_id = {row["trigger_id"]: row for row in resolution_rows}

    binary_rows = [row for row in resolution_rows if row["resolution_status"] in BINARY_STATUSES]
    true_count = sum(row["resolution_status"] == "RESOLVED_TRUE" for row in binary_rows)
    false_count = sum(row["resolution_status"] == "RESOLVED_FALSE" for row in binary_rows)
    unresolvable_definition_count = sum(
        row["resolution_status"] == "UNRESOLVABLE_DEFINITION" for row in resolution_rows
    )
    unresolvable_corporate_count = sum(
        row["resolution_status"] == "UNRESOLVABLE_CORPORATE" for row in resolution_rows
    )
    unresolvable_count = unresolvable_definition_count + unresolvable_corporate_count

    brier_values: list[float] = []
    bin_observations: dict[str, list[tuple[Decimal, int]]] = {str(item["label"]): [] for item in bins}
    for resolution in binary_rows:
        trigger = trigger_by_id[resolution["trigger_id"]]
        probability = Decimal(trigger["probability_holds"])
        outcome = 1 if resolution["resolution_status"] == "RESOLVED_TRUE" else 0
        brier_values.append(float((probability - Decimal(outcome)) ** 2))
        bin_observations[_bin_label(probability, bins)].append((probability, outcome))

    probability_bin_counts: dict[str, int] = {}
    observed_hold_rate_by_bin: dict[str, float | None] = {}
    mean_predicted_probability_by_bin: dict[str, float | None] = {}
    confidence_interval_by_bin: dict[str, dict[str, Any]] = {}
    confidence_level = float(str(policy_config["reporting_rules"].get("confidence_level", "0.95")))
    for item in bins:
        label = str(item["label"])
        observations = bin_observations[label]
        successes = sum(outcome for _, outcome in observations)
        probability_bin_counts[label] = len(observations)
        observed_hold_rate_by_bin[label] = _rate(successes, len(observations))
        mean_predicted_probability_by_bin[label] = (
            _rounded(float(sum((probability for probability, _ in observations), Decimal("0")) / len(observations)))
            if observations
            else None
        )
        confidence_interval_by_bin[label] = wilson_interval(
            successes,
            len(observations),
            confidence_level=confidence_level,
        )

    open_rows = [row for row in active if row["trigger_id"] not in resolution_by_id]
    overdue_rows = [row for row in open_rows if as_of > _parse_date(row["resolution_deadline"], "resolution_deadline")]
    active_probabilities = [Decimal(row["probability_holds"]) for row in active]
    high_probability_count = sum(probability > Decimal("0.90") for probability in active_probabilities)
    middle_probability_count = sum(
        Decimal("0.35") <= probability <= Decimal("0.75") for probability in active_probabilities
    )
    trigger_probability_histogram = {str(item["label"]): 0 for item in bins}
    for probability in active_probabilities:
        trigger_probability_histogram[_bin_label(probability, bins)] += 1

    per_decision = Counter(row["decision_id"] for row in active)
    triggers_per_decision_distribution = Counter(per_decision.values())
    decision_months = {row["locked_at"][:7] for row in active}
    resolved_decisions = {
        trigger_by_id[row["trigger_id"]]["decision_id"]
        for row in resolution_rows
    }
    share_high = _rate(high_probability_count, len(active))
    minimum_design_n = int(policy_config["reporting_rules"].get("trigger_design_review_min_n", 10))
    high_share_limit = float(
        str(policy_config["reporting_rules"].get("trigger_design_review_share_p_above_0_90", "0.80"))
    )
    if len(active) < minimum_design_n:
        design_status = "INSUFFICIENT_DATA_FOR_DESIGN_REVIEW"
    elif share_high is not None and share_high > high_share_limit:
        design_status = "TRIGGER_DESIGN_REVIEW"
    else:
        design_status = "MONITOR"

    decision_ids = [str(row.get("decision_id", "") or "").strip() for row in decision_rows]
    if any(not decision_id for decision_id in decision_ids):
        raise ValueError("decision journal contains a blank decision_id")
    if len(set(decision_ids)) != len(decision_ids):
        raise ValueError("decision journal contains duplicate decision_id values")
    missing_decision_links = sorted(
        {row["decision_id"] for row in trigger_rows}.difference(decision_ids)
    )
    if missing_decision_links:
        raise ValueError(
            "trigger ledger references decision_id values absent from Decision Capture: "
            + ", ".join(missing_decision_links)
        )

    return {
        "schema_version": "1",
        "policy_version": str(policy_config.get("policy_version", "") or ""),
        "as_of_date": as_of.isoformat(),
        "operational_forward_validation_status": _operational_status(len(decision_rows), len(active)),
        "inference_mode": "EXPLORATORY",
        "evidence_status": "DESCRIPTIVE_ONLY",
        "confirmatory_status": "INSUFFICIENT_FOR_CONFIRMATORY_INFERENCE",
        "confirmatory_registration_enabled": False,
        "resolved_trigger_count": len(resolution_rows),
        "binary_resolved_trigger_count": len(binary_rows),
        "resolved_decision_count": len(resolved_decisions),
        "decision_month_count": len(decision_months),
        "true_count": true_count,
        "false_count": false_count,
        "unresolvable_definition_count": unresolvable_definition_count,
        "unresolvable_corporate_count": unresolvable_corporate_count,
        "unresolvable_rate": _rate(unresolvable_count, len(resolution_rows)),
        "open_count": len(open_rows),
        "overdue_count": len(overdue_rows),
        "overdue_rate": _rate(len(overdue_rows), len(open_rows)),
        "rate_confidence_intervals": {
            "overall_hold_rate": wilson_interval(true_count, len(binary_rows), confidence_level=confidence_level),
            "unresolvable_rate": wilson_interval(
                unresolvable_count,
                len(resolution_rows),
                confidence_level=confidence_level,
            ),
            "overdue_rate": wilson_interval(
                len(overdue_rows),
                len(open_rows),
                confidence_level=confidence_level,
            ),
        },
        "mean_brier_score": _rounded(sum(brier_values) / len(brier_values)) if brier_values else None,
        "probability_bin_counts": probability_bin_counts,
        "observed_hold_rate_by_bin": observed_hold_rate_by_bin,
        "mean_predicted_probability_by_bin": mean_predicted_probability_by_bin,
        "confidence_interval_by_bin": confidence_interval_by_bin,
        "triggers_per_decision_distribution": {
            str(trigger_count): decision_frequency
            for trigger_count, decision_frequency in sorted(triggers_per_decision_distribution.items())
        },
        "share_p_above_0_90": share_high,
        "share_p_between_0_35_and_0_75": _rate(middle_probability_count, len(active)),
        "trigger_probability_histogram": trigger_probability_histogram,
        "claim_type_distribution": dict(sorted(Counter(row["claim_type"] for row in active).items())),
        "trigger_design_status": design_status,
        "cluster_counts": {
            "ledger_trigger_row_count": len(trigger_rows),
            "raw_trigger_n": len(active),
            "active_trigger_n": len(active),
            "superseded_trigger_count": len(trigger_rows) - len(active),
            "decision_count": len(per_decision),
            "decision_month_count": len(decision_months),
            "triggers_per_decision": {
                str(trigger_count): decision_frequency
                for trigger_count, decision_frequency in sorted(triggers_per_decision_distribution.items())
            },
            "unit": "trigger",
            "cluster_keys": ["decision_month", "decision_id"],
            "empirical_icc_status": "NOT_ESTIMATED",
            "effective_n": None,
        },
        "analysis_notes": [
            "UNRESOLVABLE outcomes are excluded from Brier and binary calibration, and reported separately.",
            "Superseded ledger rows remain in audit history but are excluded from active open/due and design counts.",
            "No empirical ICC or guessed effective sample size is reported.",
        ],
    }


def render_markdown_report(summary: Mapping[str, Any]) -> str:
    def display(value: Any) -> str:
        return "NOT_AVAILABLE" if value is None else str(value)

    lines = [
        "# Personal Forward Validation",
        "",
        f"As of: `{summary['as_of_date']}`",
        "",
        f"Operational status: `{summary['operational_forward_validation_status']}`",
        "",
        "`EXPLORATORY` / `DESCRIPTIVE_ONLY` / `INSUFFICIENT_FOR_CONFIRMATORY_INFERENCE`",
        "",
        "## Outcome diagnostics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key in [
        "resolved_trigger_count",
        "resolved_decision_count",
        "true_count",
        "false_count",
        "unresolvable_definition_count",
        "unresolvable_corporate_count",
        "unresolvable_rate",
        "open_count",
        "overdue_count",
        "overdue_rate",
        "mean_brier_score",
    ]:
        value = summary[key]
        lines.append(f"| `{key}` | {display(value)} |")

    lines.extend(
        [
            "",
            "## Binary-rate intervals",
            "",
            "| Rate | n | Estimate | Wilson lower | Wilson upper |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for label, interval in summary["rate_confidence_intervals"].items():
        values = [
            label,
            interval["n"],
            interval["estimate"],
            interval["lower_ci"],
            interval["upper_ci"],
        ]
        lines.append("| " + " | ".join(display(value) for value in values) + " |")

    lines.extend(
        [
            "",
            "## Calibration bins",
            "",
            "| Bin | n | Mean p | Hold rate | Wilson lower | Wilson upper |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for label, n in summary["probability_bin_counts"].items():
        interval = summary["confidence_interval_by_bin"][label]
        values = [
            label,
            n,
            summary["mean_predicted_probability_by_bin"][label],
            summary["observed_hold_rate_by_bin"][label],
            interval["lower_ci"],
            interval["upper_ci"],
        ]
        lines.append("| " + " | ".join(display(value) for value in values) + " |")

    cluster = summary["cluster_counts"]
    lines.extend(
        [
            "",
            "## Trigger design and dependence",
            "",
            f"- Design status: `{summary['trigger_design_status']}`",
            f"- Raw active triggers: `{cluster['raw_trigger_n']}`",
            f"- Decisions: `{cluster['decision_count']}`",
            f"- Decision months: `{cluster['decision_month_count']}`",
            f"- Empirical ICC: `{cluster['empirical_icc_status']}`",
            f"- Share p > 0.90: `{display(summary['share_p_above_0_90'])}`",
            f"- Share p in [0.35, 0.75]: `{display(summary['share_p_between_0_35_and_0_75'])}`",
            "",
            "### Active-trigger probability histogram",
            "",
            "| Bin | Trigger count |",
            "|---|---:|",
        ]
    )
    for label, count in summary["trigger_probability_histogram"].items():
        lines.append(f"| {label} | {count} |")
    lines.extend(
        [
            "",
            "### Claim-type distribution",
            "",
            "| Claim type | Trigger count |",
            "|---|---:|",
        ]
    )
    if summary["claim_type_distribution"]:
        for label, count in summary["claim_type_distribution"].items():
            lines.append(f"| {label} | {count} |")
    else:
        lines.append("| NOT_AVAILABLE | 0 |")
    lines.extend(
        [
            "",
            "### Triggers per decision",
            "",
            "| Trigger count | Decision frequency |",
            "|---|---:|",
        ]
    )
    if summary["triggers_per_decision_distribution"]:
        for trigger_count, frequency in summary["triggers_per_decision_distribution"].items():
            lines.append(f"| {trigger_count} | {frequency} |")
    else:
        lines.append("| NOT_AVAILABLE | 0 |")
    lines.extend(
        [
            "",
            "Unresolvable outcomes are not binary outcomes. No confirmatory inference, policy promotion,",
            "investment decision, trigger lock, or resolution confirmation is performed by this report.",
            "",
        ]
    )
    return "\n".join(lines)


def write_forward_validation_outputs(
    *,
    as_of_date: str,
    trigger_ledger: str = DEFAULT_TRIGGER_LEDGER,
    resolution_ledger: str = DEFAULT_RESOLUTION_LEDGER,
    decision_journal: str = DEFAULT_DECISION_JOURNAL,
    policy: str = DEFAULT_POLICY,
    summary_output: str = DEFAULT_SUMMARY_OUTPUT,
    report_output: str | None = None,
) -> tuple[Path, Path]:
    trigger_rows = load_trigger_ledger(trigger_ledger)
    resolution_rows = load_resolution_ledger(resolution_ledger)
    decision_path = resolve_repo_path(decision_journal)
    decision_rows = read_csv_rows(decision_path) if decision_path.exists() else []
    summary = build_forward_validation_summary(
        trigger_rows=trigger_rows,
        resolution_rows=resolution_rows,
        decision_rows=decision_rows,
        policy_config=load_yaml_config(policy),
        as_of_date=as_of_date,
    )
    summary_path = ensure_parent_dir(summary_output)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path = ensure_parent_dir(
        report_output or DEFAULT_REPORT_TEMPLATE.format(as_of_date=summary["as_of_date"])
    )
    report_path.write_text(render_markdown_report(summary), encoding="utf-8")
    return summary_path, report_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build descriptive forward-validation diagnostics from processed ledgers.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    report = subparsers.add_parser("report")
    report.add_argument("--as-of-date", required=True)
    report.add_argument("--trigger-ledger", default=DEFAULT_TRIGGER_LEDGER)
    report.add_argument("--resolution-ledger", default=DEFAULT_RESOLUTION_LEDGER)
    report.add_argument("--decision-journal", default=DEFAULT_DECISION_JOURNAL)
    report.add_argument("--policy", default=DEFAULT_POLICY)
    report.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    report.add_argument("--report-output")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        summary, report = write_forward_validation_outputs(
            as_of_date=args.as_of_date,
            trigger_ledger=args.trigger_ledger,
            resolution_ledger=args.resolution_ledger,
            decision_journal=args.decision_journal,
            policy=args.policy,
            summary_output=args.summary_output,
            report_output=args.report_output,
        )
        print(f"forward_validation_summary={summary}")
        print(f"forward_validation_report={report}")
        print("inference_mode=EXPLORATORY")
        print("evidence_status=DESCRIPTIVE_ONLY")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
