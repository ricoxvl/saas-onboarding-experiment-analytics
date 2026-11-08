"""Exploratory segment effects, treatment guardrails and baseline checks."""
import math

from .power import design_sensitivity


def benjamini_hochberg(pvalues):
    """BH-adjusted q values for one declared exploratory test family."""
    if any(not 0 <= p <= 1 for p in pvalues):
        raise ValueError("p values must be between 0 and 1")
    m = len(pvalues)
    if not m:
        return []
    order = sorted(range(m), key=lambda i: pvalues[i])
    q = [0.0] * m
    running = 1.0
    for rank in range(m, 0, -1):
        index = order[rank - 1]
        running = min(running, pvalues[index] * m / rank)
        q[index] = round(running, 6)
    return q


def _rows_by_arm(conn, metric, where="", params=()):
    allowed = {
        "returned_d28", "activated_d7", "onboarding_error_d7", "support_ticket_d7"
    }
    if metric not in allowed:
        raise ValueError("unknown metric")
    rows = conn.execute(
        f"SELECT variant, COUNT(*) AS n, SUM({metric}) AS successes "
        f"FROM users {where} GROUP BY variant", params
    )
    return {r["variant"]: dict(r) for r in rows}


def segmented_results(conn, compare_binary):
    """Exploratory treatment-vs-control contrasts with a single BH-FDR family."""
    results = []
    for dimension in ("segment", "signup_month"):
        levels = [r[0] for r in conn.execute(
            f"SELECT DISTINCT {dimension} FROM users ORDER BY {dimension}"
        )]
        for level in levels:
            arms = _rows_by_arm(conn, "returned_d28", f"WHERE {dimension} = ?", (level,))
            if set(arms) != {"control", "treatment"}:
                continue
            t, c = arms["treatment"], arms["control"]
            effect = compare_binary(t["successes"], t["n"], c["successes"], c["n"])
            results.append({
                "dimension": dimension, "level": level,
                "control_n": c["n"], "treatment_n": t["n"], **effect,
            })

    qvalues = benjamini_hochberg([r["p_value_two_sided"] for r in results])
    for item, qvalue in zip(results, qvalues):
        item["exploratory_bh_fdr_q_value"] = qvalue
    return {
        "warning": "exploratory_subgroups_not_confirmatory_or_randomized_separately",
        "multiplicity": "BH_FDR_across_all_retention_subgroup_contrasts",
        "contrasts": results,
    }


def guardrail_results(conn, compare_binary):
    """Post-signup user-level negative outcomes; lower is better."""
    result = {}
    for metric, risk_limit_pp in (
        ("onboarding_error_d7", 2),
        ("support_ticket_d7", 2),
    ):
        rows = _rows_by_arm(conn, metric)
        t, c = rows["treatment"], rows["control"]
        effect = compare_binary(t["successes"], t["n"], c["successes"], c["n"])
        high_ci = effect["confidence_interval_95_pp"][1]
        result[metric] = {
            **effect, "direction": "lower_is_better",
            "illustrative_max_tolerable_increase_pp": risk_limit_pp,
            "upper_95_ci_below_risk_limit": high_ci < risk_limit_pp,
            "interpretation": "illustrative_guardrail_not_a_pre_registered_live_test",
        }
    return result


def assignment_balance(conn):
    """Describe pre-treatment team/solo mix by arm (not a replacement for SRM)."""
    rows = [dict(r) for r in conn.execute("""
        SELECT variant, COUNT(*) AS n,
               SUM(CASE WHEN segment = 'team' THEN 1 ELSE 0 END) AS team_n
        FROM users GROUP BY variant
    """)]
    by_arm = {r["variant"]: r for r in rows}
    p = {k: v["team_n"] / v["n"] for k, v in by_arm.items()}
    variance = (p["treatment"] * (1 - p["treatment"]) +
                p["control"] * (1 - p["control"])) / 2
    smd = (p["treatment"] - p["control"]) / math.sqrt(variance) if variance else 0.0
    return {
        "team_share_by_variant": {k: round(v, 6) for k, v in p.items()},
        "team_share_standardized_difference": round(smd, 4),
        "absolute_smd_gt_0_1": abs(smd) > 0.1,
        "note": "descriptive randomization diagnostic, not a formal allocation test",
    }


def analyze_advanced(conn, compare_binary, baseline_rate, t_n, c_n):
    return {
        "guardrails": guardrail_results(conn, compare_binary),
        "exploratory_retention_segments": segmented_results(conn, compare_binary),
        "assignment_balance": assignment_balance(conn),
        "planning_sensitivity": design_sensitivity(baseline_rate, t_n, c_n),
    }
