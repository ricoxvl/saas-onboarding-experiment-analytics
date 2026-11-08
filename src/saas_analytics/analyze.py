"""Analyze synthetic SaaS onboarding cohorts and A/B results from SQLite."""
import csv
import json
import math
import sqlite3
from pathlib import Path

from .simulate import DATA, ROOT


def two_sided_pvalue(z):
    return math.erfc(abs(z) / math.sqrt(2))


def compare_binary(treatment_success, treatment_n, control_success, control_n):
    if min(treatment_n, control_n) < 1:
        raise ValueError("Both variants must have users")
    pt = treatment_success / treatment_n
    pc = control_success / control_n
    difference = pt - pc
    standard_error = math.sqrt(pt * (1 - pt) / treatment_n + pc * (1 - pc) / control_n)
    pooled = (treatment_success + control_success) / (treatment_n + control_n)
    null_se = math.sqrt(pooled * (1 - pooled) * (1 / treatment_n + 1 / control_n))
    z = difference / null_se if null_se > 0 else 0.0
    return {
        "control_rate": round(pc, 6),
        "treatment_rate": round(pt, 6),
        "absolute_lift_pp": round(100 * difference, 3),
        "relative_lift_pct": round(100 * difference / pc, 3) if pc else None,
        "confidence_interval_95_pp": [
            round(100 * (difference - 1.96 * standard_error), 3),
            round(100 * (difference + 1.96 * standard_error), 3),
        ],
        "z_statistic": round(z, 4),
        "p_value_two_sided": round(two_sided_pvalue(z), 6),
    }


def analyze(database=DATA / "saas.db", reports_dir=ROOT / "reports" / "generated"):
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as conn:
        conn.row_factory = sqlite3.Row
        summary = {
            row["variant"]: dict(row)
            for row in conn.execute("""
                SELECT variant, COUNT(*) AS users,
                       SUM(activated_d7) AS activated,
                       SUM(returned_d28) AS retained
                FROM users GROUP BY variant
            """)
        }
        if set(summary) != {"control", "treatment"}:
            raise ValueError("Both experiment groups are required")
        funnel = [dict(row) for row in conn.execute("""
            SELECT variant, COUNT(*) AS signups,
                   SUM(workspace_created) AS workspace_created,
                   SUM(integration_connected) AS integration_connected,
                   SUM(teammate_invited) AS teammate_invited,
                   SUM(activated_d7) AS activated_d7
            FROM users GROUP BY variant ORDER BY variant
        """)]
        cohorts = [dict(row) for row in conn.execute("""
            SELECT signup_month, variant, COUNT(*) AS users,
                   SUM(activated_d7) AS activated_d7,
                   SUM(returned_d28) AS returned_d28
            FROM users GROUP BY signup_month, variant
            ORDER BY signup_month, variant
        """)]

    t, c = summary["treatment"], summary["control"]
    n = t["users"] + c["users"]
    # Pearson chi-square statistic for expected 1:1 assignment, df=1.
    chi2 = ((t["users"] - n / 2) ** 2 + (c["users"] - n / 2) ** 2) / (n / 2)
    srm_p = math.erfc(math.sqrt(chi2 / 2))
    result = {
        "data_source": "synthetic_simulation_not_real_customers",
        "users_total": n,
        "by_variant": summary,
        "primary_metric": "returned_d28",
        "retention_d28": compare_binary(t["retained"], t["users"], c["retained"], c["users"]),
        "activation_d7": compare_binary(t["activated"], t["users"], c["activated"], c["users"]),
        "srm": {"expected_allocation": "50/50", "chi_square": round(chi2, 4),
                "p_value": round(srm_p, 6), "flag_p_below_0_001": srm_p < 0.001},
    }

    (reports_dir / "experiment_results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    for name, rows in [("funnel.csv", funnel), ("cohorts.csv", cohorts)]:
        with (reports_dir / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    r = result["retention_d28"]
    low, high = r["confidence_interval_95_pp"]
    decision = (
        "The simulated data show a statistically detectable difference at alpha=0.05."
        if r["p_value_two_sided"] < 0.05
        else "The simulated data do not establish a statistically detectable difference at alpha=0.05."
    )
    report = f"""# Synthetic SaaS onboarding experiment results

**Not production evidence.** This report uses simulated users and preselected fictional behavior probabilities.

- Sample: {n:,} users; treatment {t['users']:,}, control {c['users']:,}
- Day-28 retention: treatment {r['treatment_rate']:.1%}, control {r['control_rate']:.1%}
- Absolute difference: {r['absolute_lift_pp']:+.2f} percentage points
- 95% confidence interval: [{low:+.2f}, {high:+.2f}] percentage points
- Two-sided p-value: {r['p_value_two_sided']:.4f}
- SRM p-value: {srm_p:.4f}; flagged at p < 0.001: {result['srm']['flag_p_below_0_001']}

## Interpretation

{decision} This is a demonstration of analysis methods, not evidence that any live product change improved retention.

## Caveats

Normal approximation, no adjustment for multiple tests, no production telemetry, and synthetic event generation. Day-28 activity is measured as an event on day 28, not a 28-day cumulative retention window.
"""
    (reports_dir / "summary.md").write_text(report, encoding="utf-8")
    return result


def main():
    result = analyze()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
