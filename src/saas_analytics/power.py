"""Prospective experiment sample-size and MDE approximations (not observed power)."""
import math
from statistics import NormalDist


def _check_design(baseline_rate, alpha, power):
    if not 0 < baseline_rate < 1:
        raise ValueError("baseline_rate must be strictly between 0 and 1")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be strictly between 0 and 1")
    if not 0.5 < power < 1:
        raise ValueError("power must be between 0.5 and 1")


def required_per_arm(baseline_rate, absolute_effect, alpha=0.05, power=0.80):
    """Approximate per-arm n for a positive two-sided difference in proportions.

    Uses the standard normal-approximation planning formula with 1:1 allocation.
    This is an approximation, not an exact binomial power calculation.
    """
    _check_design(baseline_rate, alpha, power)
    if not 0 < absolute_effect < 1 - baseline_rate:
        raise ValueError("absolute_effect must be positive and keep treatment rate below 1")
    pt = baseline_rate + absolute_effect
    pooled = (baseline_rate + pt) / 2
    za = NormalDist().inv_cdf(1 - alpha / 2)
    zb = NormalDist().inv_cdf(power)
    numerator = (
        za * math.sqrt(2 * pooled * (1 - pooled))
        + zb * math.sqrt(baseline_rate * (1 - baseline_rate) + pt * (1 - pt))
    ) ** 2
    return math.ceil(numerator / (absolute_effect ** 2))


def minimum_detectable_effect_pp(baseline_rate, per_arm, alpha=0.05, power=0.80):
    """Smallest positive effect in percentage points detectable at a given per-arm n.

    Returns None if even the mathematical maximum increase is beyond this design's
    approximate 80%-power reach. Unequal allocation can be approximated with
    the smaller arm size (conservative).
    """
    _check_design(baseline_rate, alpha, power)
    if not isinstance(per_arm, int) or per_arm < 2:
        raise ValueError("per_arm must be an integer of at least 2")
    lo, hi = 0.0, 1 - baseline_rate
    epsilon = 1e-10
    if required_per_arm(baseline_rate, hi - epsilon, alpha, power) > per_arm:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if required_per_arm(baseline_rate, mid, alpha, power) <= per_arm:
            hi = mid
        else:
            lo = mid
    return round(100 * hi, 3)


def design_sensitivity(baseline_rate, treatment_n, control_n, alpha=0.05, power=0.80):
    """Scenario planning using a reference baseline; not post-hoc achieved power."""
    usable_n = min(treatment_n, control_n)
    effects_pp = (2, 3, 5)
    return {
        "interpretation": "prospective_normal_approximation_not_observed_power",
        "reference_baseline_rate": round(baseline_rate, 6),
        "alpha_two_sided": alpha,
        "target_power": power,
        "current_minimum_arm_n": usable_n,
        "mde_absolute_pp_approx": minimum_detectable_effect_pp(
            baseline_rate, usable_n, alpha, power
        ),
        "required_total_n_balanced_by_effect": [
            {
                "effect_pp": e,
                "required_n_per_arm": required_per_arm(
                    baseline_rate, e / 100, alpha, power
                ),
                "required_total_n": 2 * required_per_arm(
                    baseline_rate, e / 100, alpha, power
                ),
            }
            for e in effects_pp
            if baseline_rate + e / 100 < 1
        ],
    }
