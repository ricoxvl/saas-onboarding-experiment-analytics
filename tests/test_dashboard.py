"""Dashboard aggregations must agree with validated SQLite experiment totals."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from dashboard.data import (
    aggregate_kpis, arm_summary, cohort_rows, compare_metric,
    experiment_summary, exploratory_segments, funnel_rows,
    load_verified_users, select_users,
)
from saas_analytics.analyze import analyze
from saas_analytics.simulate import generate


class DashboardDataTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        generate(users=600, seed=42, output_dir=self.path)
        self.users, self.quality = load_verified_users(self.path / "saas.db")

    def test_validated_load_and_filters(self):
        self.assertTrue(self.quality["passed"])
        self.assertEqual(len(self.users), 600)
        self.assertEqual(len(select_users(self.users)), 600)
        self.assertEqual(
            sum(len(select_users(self.users, segment=s)) for s in ("solo", "team")),
            600,
        )
        month = self.users[0]["signup_month"]
        filtered = select_users(self.users, months=[month], segment="team")
        self.assertTrue(all(
            r["signup_month"] == month and r["segment"] == "team"
            for r in filtered
        ))
        self.assertEqual(select_users(self.users, months=[]), [])
        with self.assertRaises(ValueError):
            select_users(self.users, segment="unknown")

    def test_funnel_and_kpis_reconcile(self):
        all_kpis = aggregate_kpis(self.users)
        self.assertEqual(all_kpis["users"], 600)
        rows = funnel_rows(self.users)
        self.assertEqual(len(rows), 8)
        for v in ("control", "treatment"):
            arm = arm_summary(self.users)[v]
            steps = [r["users"] for r in rows if r["variant"] == v]
            self.assertEqual(steps[0], arm["users"])
            self.assertTrue(all(a >= b for a, b in zip(steps, steps[1:])))
        self.assertEqual(sum(r["users"] for r in cohort_rows(self.users)), 600)

    def test_primary_reconciles_to_existing_pipeline(self):
        actual = analyze(self.path / "saas.db", self.path / "reports")
        dash = compare_metric(self.users, "returned_d28")
        self.assertEqual(dash["absolute_lift_pp"], actual["retention_d28"]["absolute_lift_pp"])
        self.assertEqual(dash["p_value_two_sided"], actual["retention_d28"]["p_value_two_sided"])
        self.assertEqual(dash["confidence_interval_95_pp"], actual["retention_d28"]["confidence_interval_95_pp"])
        exp = experiment_summary(self.users)
        self.assertEqual(exp["allocation"]["control_n"], actual["by_variant"]["control"]["users"])
        self.assertEqual(exp["allocation"]["treatment_n"], actual["by_variant"]["treatment"]["users"])
        for guardrail in ("onboarding_error_d7", "support_ticket_d7"):
            self.assertEqual(
                exp["comparisons"][guardrail]["absolute_lift_pp"],
                actual["guardrails"][guardrail]["absolute_lift_pp"],
            )
        self.assertGreater(exp["planning"]["current_minimum_arm_n"], 0)

    def test_subgroups_adjustment_and_bounds(self):
        rows = exploratory_segments(self.users)
        self.assertGreaterEqual(len(rows), 4)
        self.assertTrue(all(
            0 <= r["p_value"] <= r["bh_fdr_q_value"] <= 1 for r in rows
        ))
        months = {r["signup_month"] for r in self.users}
        self.assertEqual(
            len([r for r in rows if r["dimension"] == "signup_month"]),
            len(months),
        )

    def test_fails_closed_if_event_corrupt(self):
        with sqlite3.connect(self.path / "saas.db") as conn:
            conn.execute("DELETE FROM events WHERE event_name = 'signup' AND user_id = 'u000001'")
        with self.assertRaisesRegex(ValueError, "Data-quality audit failed"):
            load_verified_users(self.path / "saas.db")

    def test_empty_and_missing_arms(self):
        self.assertEqual(aggregate_kpis([])["users"], 0)
        self.assertEqual(funnel_rows([])[0]["users"], 0)
        self.assertIsNone(experiment_summary([]))
        self.assertIsNone(compare_metric([], "returned_d28"))
        with self.assertRaises(ValueError):
            compare_metric(self.users, "nonexistent_metric")


if __name__ == "__main__":
    unittest.main()
