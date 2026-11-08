"""Pure-Python, tested dashboard analytics over validated synthetic user records.

Keeping filtering and aggregation separate from Streamlit makes it easier to
verify dashboard figures against the underlying experiment pipeline.
"""
import math
import sqlite3
from collections import defaultdict
from pathlib import Path

from saas_analytics.analyze import compare_binary
from saas_analytics.advanced import benjamini_hochberg
from saas_analytics.power import design_sensitivity
from saas_analytics.quality import audit_database

VARIANTS = ("control", "treatment")
METRICS = (
    "activated_d7", "returned_d28",
    "onboarding_error_d7", "support_ticket_d7",
)
FUNNEL_STEPS = (
    ("Signups", None),
    ("Workspace created", "workspace_created"),
    ("Integration connected", "integration_connected"),
    ("Activated by D7", "activated_d7"),
)


def load_verified_users(database):
    """Read the SQLite model after event-level validation; fail closed."""
    path = Path(database)
    if not path.is_file():
        raise FileNotFoundError(f"Database not found: {path}")
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        quality = audit_database(conn)
        if not quality["passed"]:
            raise ValueError(f"Data-quality audit failed: {quality['issue_counts']}")
        users = [dict(row) for row in conn.execute("SELECT * FROM users ORDER BY user_id")]
    return users, quality


def select_users(users, segment="All users", months=None):
    """Filter by a pre-treatment segment and signup cohorts, not by outcomes."""
    if segment not in ("All users", "solo", "team"):
        raise ValueError(f"Unknown segment: {segment}")
    selected_months = set(months) if months is not None else None
    return [
        user for user in users
        if (segment == "All users" or user["segment"] == segment)
        and (selected_months is None or user["signup_month"] in selected_months)
    ]


def arm_summary(users):
    result = {
        v: {"variant": v, "users": 0, **{k: 0 for k in METRICS}}
        for v in VARIANTS
    }
    for u in users:
        v = u["variant"]
        item = result[v]
        item["users"] += 1
        for k in METRICS:
            item[k] += u[k]
    return result


def aggregate_kpis(users):
    n = len(users)
    if not n:
        return {"users": 0, **{k: 0 for k in METRICS}}
    return {
        "users": n,
        **{k: sum(u[k] for u in users) / n for k in METRICS},
    }


def funnel_rows(users):
    arms = {v: [u for u in users if u["variant"] == v] for v in VARIANTS}
    rows = []
    for v, group in arms.items():
        n = len(group)
        for step, col in FUNNEL_STEPS:
            count = n if col is None else sum(u[col] for u in group)
            rows.append({
                "variant": v, "step": step,
                "users": count, "rate_pct": round(100 * count / n, 2) if n else 0,
            })
    return rows


def cohort_rows(users):
    groups = defaultdict(list)
    for u in users:
        groups[(u["signup_month"], u["variant"])].append(u)
    rows = []
    for (month, variant), group in sorted(groups.items()):
        n = len(group)
        rows.append({
            "signup_month": month,
            "variant": variant,
            "users": n,
            "activation_pct": round(100 * sum(u["activated_d7"] for u in group) / n, 2),
            "retention_d28_pct": round(100 * sum(u["returned_d28"] for u in group) / n, 2),
        })
    return rows


def compare_metric(users, field):
    """Compare treatment-control within the selected pre-treatment population."""
    if field not in METRICS:
        raise ValueError(f"Unknown metric: {field}")
    arms = arm_summary(users)
    c, t = arms["control"], arms["treatment"]
    if not c["users"] or not t["users"]:
        return None
    effect = compare_binary(t[field], t["users"], c[field], c["users"])
    return {
        "metric": field,
        "control_n": c["users"],
        "treatment_n": t["users"],
        "control_success": c[field],
        "treatment_success": t[field],
        **effect,
    }


def experiment_summary(users, tolerance_pp=2.0):
    """Live re-computation for filtered *synthetic* cohorts; no causal deployment claim."""
    if tolerance_pp < 0:
        raise ValueError("tolerance_pp must be nonnegative")
    comparisons = {metric: compare_metric(users, metric) for metric in METRICS}
    if any(value is None for value in comparisons.values()):
        return None
    arms = arm_summary(users)
    t, c = arms["treatment"]["users"], arms["control"]["users"]
    total = t + c
    chi_square = ((t - total / 2) ** 2 + (c - total / 2) ** 2) / (total / 2)
    srm_p = math.erfc(math.sqrt(chi_square / 2))
    guardrail_status = {}
    for metric in ("onboarding_error_d7", "support_ticket_d7"):
        estimate = comparisons[metric]
        guardrail_status[metric] = {
            "tolerance_pp": tolerance_pp,
            "upper_confidence_bound_pp": estimate["confidence_interval_95_pp"][1],
            "upper_bound_within_tolerance": estimate["confidence_interval_95_pp"][1] < tolerance_pp,
        }
    return {
        "comparisons": comparisons,
        "guardrails": guardrail_status,
        "allocation": {
            "control_n": c, "treatment_n": t,
            "srm_p_value": round(srm_p, 6),
            "srm_flag": srm_p < 0.001,
        },
        "planning": design_sensitivity(
            baseline_rate=comparisons["returned_d28"]["control_rate"],
            treatment_n=t,
            control_n=c,
        ),
    }


def exploratory_segments(users):
    """Subgroup effects with BH-FDR across a single visible family of contrasts."""
    rows = []
    for dimension in ("segment", "signup_month"):
        levels = sorted({u[dimension] for u in users})
        for level in levels:
            subset = [u for u in users if u[dimension] == level]
            effect = compare_metric(subset, "returned_d28")
            if effect is not None:
                rows.append({
                    "dimension": dimension,
                    "level": level,
                    "control_n": effect["control_n"],
                    "treatment_n": effect["treatment_n"],
                    "control_pct": round(effect["control_rate"] * 100, 2),
                    "treatment_pct": round(effect["treatment_rate"] * 100, 2),
                    "lift_pp": effect["absolute_lift_pp"],
                    "p_value": effect["p_value_two_sided"],
                })
    adjusted = benjamini_hochberg([r["p_value"] for r in rows])
    for row, q in zip(rows, adjusted):
        row["bh_fdr_q_value"] = q
    return rows
