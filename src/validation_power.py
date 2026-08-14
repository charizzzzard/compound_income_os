from __future__ import annotations

import argparse
import json
import math
from statistics import NormalDist
from typing import Any


POWER_PLANNING_APPROXIMATION = "POWER_PLANNING_APPROXIMATION"
MEAN_TEST_TYPES = {"one_sample", "two_sample"}
CORRELATION_METHODS = {"pearson", "spearman"}
ALTERNATIVES = {"two_sided", "one_sided"}


def _require_finite_positive(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name} must be finite and > 0")
    return number


def _require_probability(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0.0 < number < 1.0:
        raise ValueError(f"{name} must be between 0 and 1, exclusive")
    return number


def _critical_z(alpha: float, alternative: str) -> float:
    if alternative not in ALTERNATIVES:
        raise ValueError(f"alternative must be one of {sorted(ALTERNATIVES)}")
    tail_alpha = alpha / 2.0 if alternative == "two_sided" else alpha
    return NormalDist().inv_cdf(1.0 - tail_alpha)


def _planning_z_sum(alpha: float, power: float, alternative: str) -> float:
    return _critical_z(alpha, alternative) + NormalDist().inv_cdf(power)


def required_n_mean(
    effect: float,
    sigma: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    test_type: str = "one_sample",
    alternative: str = "two_sided",
) -> dict[str, Any]:
    """Plan a normal-approximation mean test.

    ``effect`` is the absolute mean difference to detect. For ``two_sample``,
    equal group sizes and the same within-group ``sigma`` are assumed. The
    result separates per-group and total sample sizes so the factor of two is
    explicit.
    """

    delta = _require_finite_positive("effect", abs(float(effect)))
    standard_deviation = _require_finite_positive("sigma", sigma)
    significance = _require_probability("alpha", alpha)
    target_power = _require_probability("power", power)
    if test_type not in MEAN_TEST_TYPES:
        raise ValueError(f"test_type must be one of {sorted(MEAN_TEST_TYPES)}")

    z_sum = _planning_z_sum(significance, target_power, alternative)
    one_sample_information = (z_sum * standard_deviation / delta) ** 2
    result: dict[str, Any] = {
        "test_type": test_type,
        "alpha": significance,
        "power": target_power,
        "effect": delta,
        "sigma": standard_deviation,
        "alternative": alternative,
        "planning_status": POWER_PLANNING_APPROXIMATION,
    }
    if test_type == "one_sample":
        result["n_total"] = math.ceil(one_sample_information)
        return result

    n_per_group = math.ceil(2.0 * one_sample_information)
    result["n_per_group"] = n_per_group
    result["n_total"] = 2 * n_per_group
    result["equal_group_sizes"] = True
    return result


def minimum_detectable_mean_effect(
    n_total: int,
    sigma: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    test_type: str = "one_sample",
    alternative: str = "two_sided",
) -> dict[str, Any]:
    """Return the mean-effect MDE under the same planning approximation."""

    if isinstance(n_total, bool) or int(n_total) != n_total or int(n_total) <= 0:
        raise ValueError("n_total must be a positive integer")
    total = int(n_total)
    standard_deviation = _require_finite_positive("sigma", sigma)
    significance = _require_probability("alpha", alpha)
    target_power = _require_probability("power", power)
    if test_type not in MEAN_TEST_TYPES:
        raise ValueError(f"test_type must be one of {sorted(MEAN_TEST_TYPES)}")
    if test_type == "two_sample" and total % 2:
        raise ValueError("two_sample n_total must be even for equal group sizes")

    z_sum = _planning_z_sum(significance, target_power, alternative)
    if test_type == "one_sample":
        effect = z_sum * standard_deviation / math.sqrt(total)
        n_per_group: int | None = None
    else:
        n_per_group = total // 2
        effect = z_sum * standard_deviation * math.sqrt(2.0 / n_per_group)

    result: dict[str, Any] = {
        "test_type": test_type,
        "n_total": total,
        "alpha": significance,
        "power": target_power,
        "sigma": standard_deviation,
        "minimum_detectable_effect": effect,
        "alternative": alternative,
        "planning_status": POWER_PLANNING_APPROXIMATION,
    }
    if n_per_group is not None:
        result["n_per_group"] = n_per_group
        result["equal_group_sizes"] = True
    return result


def required_n_correlation(
    rho: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    method: str = "pearson",
    alternative: str = "two_sided",
) -> dict[str, Any]:
    """Plan correlation sample size; this is not an exact inferential test.

    Pearson uses the Fisher-z planning approximation. Spearman applies the
    Bonett/Wright-style variance inflation ``1 + rho**2 / 2`` to the Fisher-z
    information term.
    """

    correlation = float(rho)
    if not math.isfinite(correlation) or correlation == 0.0 or abs(correlation) >= 1.0:
        raise ValueError("rho must be finite, non-zero, and strictly between -1 and 1")
    significance = _require_probability("alpha", alpha)
    target_power = _require_probability("power", power)
    normalized_method = str(method).strip().lower()
    if normalized_method not in CORRELATION_METHODS:
        raise ValueError(f"method must be one of {sorted(CORRELATION_METHODS)}")

    fisher_z = math.atanh(abs(correlation))
    base_information = (_planning_z_sum(significance, target_power, alternative) / fisher_z) ** 2
    variance_inflation = 1.0 if normalized_method == "pearson" else 1.0 + correlation**2 / 2.0
    n_total = math.ceil(3.0 + base_information * variance_inflation)
    return {
        "method": normalized_method,
        "n_total": n_total,
        "alpha": significance,
        "power": target_power,
        "rho": correlation,
        "alternative": alternative,
        "variance_inflation": variance_inflation,
        "planning_status": POWER_PLANNING_APPROXIMATION,
        "exact_inferential_test": False,
    }


def cluster_design_effect(cluster_size: float, *, icc: float) -> float:
    """Return ``1 + (cluster_size - 1) * icc`` for an explicit ICC."""

    size = _require_finite_positive("cluster_size", cluster_size)
    correlation = float(icc)
    if not math.isfinite(correlation) or not 0.0 <= correlation <= 1.0:
        raise ValueError("icc must be finite and between 0 and 1")
    return 1.0 + (size - 1.0) * correlation


def effective_n_from_design_effect(raw_n: float, design_effect: float) -> float:
    """Return descriptive effective n for an explicitly supplied design effect."""

    count = _require_finite_positive("raw_n", raw_n)
    effect = _require_finite_positive("design_effect", design_effect)
    if effect < 1.0:
        raise ValueError("design_effect must be >= 1")
    return count / effect


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic power-planning approximations for future CIOS experiments.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mean_parser = subparsers.add_parser("mean")
    mean_parser.add_argument("--effect", type=float, required=True)
    mean_parser.add_argument("--sigma", type=float, required=True)
    mean_parser.add_argument("--alpha", type=float, default=0.05)
    mean_parser.add_argument("--power", type=float, default=0.80)
    mean_parser.add_argument("--test-type", choices=sorted(MEAN_TEST_TYPES), default="one_sample")
    mean_parser.add_argument("--alternative", choices=sorted(ALTERNATIVES), default="two_sided")

    correlation_parser = subparsers.add_parser("correlation")
    correlation_parser.add_argument("--rho", type=float, required=True)
    correlation_parser.add_argument("--alpha", type=float, default=0.05)
    correlation_parser.add_argument("--power", type=float, default=0.80)
    correlation_parser.add_argument("--method", choices=sorted(CORRELATION_METHODS), default="pearson")
    correlation_parser.add_argument("--alternative", choices=sorted(ALTERNATIVES), default="two_sided")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    if args.command == "mean":
        result = required_n_mean(
            args.effect,
            args.sigma,
            alpha=args.alpha,
            power=args.power,
            test_type=args.test_type,
            alternative=args.alternative,
        )
    else:
        result = required_n_correlation(
            args.rho,
            alpha=args.alpha,
            power=args.power,
            method=args.method,
            alternative=args.alternative,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
