"""Phase 2 regression tests: guardrails, QA, FDR, and experiment planning."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from saas_analytics.advanced import benjamini_hochberg
from saas_analytics.analyze import analyze
from saas_analytics.power import minimum_detectable_effect_pp, required_per_arm
from saas_analytics.quality import audit_database
from saas_analytics.simulate import generate


class AdvancedAnalyticsTest(unittest.TestCase):
    def test_sample_size_and_mde(self):
        self.assertGreater(required_per_arm(0.50, 0.02), required_per_arm(0.50, 0.05))
        self.assertGreater(minimum_detectable_effect_pp(0.50, 250),
                           minimum_detectable_effect_pp(0.50, 2000))
        self.assertGreater(required_per_arm(0.50, 0.03, power=0.90),
                           required_per_arm(0.50, 0.03, power=0.80))
        for baseline, lift in ((0, .02), (0.5, 0), (0.99, 0.05)):
            with self.assertRaises(ValueError):
                required_per_arm(baseline, lift)

    def test_bh_correction(self):
        self.assertEqual(benjamini_hochberg([]), [])
        self.assertEqual(benjamini_hochberg([0.01, 0.04, 0.03]), [0.03, 0.04, 0.04])
        with self.assertRaises(ValueError):
            benjamini_hochberg([-0.01])

    def test_quality_and_new_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generate(1000, seed=42, output_dir=root)
            with sqlite3.connect(root / "saas.db") as conn:
                conn.row_factory = sqlite3.Row
                audit = audit_database(conn)
            self.assertTrue(audit["passed"], audit)
            result = analyze(root / "saas.db", root / "reports")
            self.assertTrue(result["data_quality"]["passed"])
            self.assertEqual(set(result["guardrails"]),
                             {"onboarding_error_d7", "support_ticket_d7"})
            self.assertGreater(len(result["exploratory_retention_segments"]["contrasts"]), 2)
            for item in result["exploratory_retention_segments"]["contrasts"]:
                self.assertGreaterEqual(item["exploratory_bh_fdr_q_value"], 0)
                self.assertLessEqual(item["exploratory_bh_fdr_q_value"], 1)
            self.assertIsNotNone(result["planning_sensitivity"]["mde_absolute_pp_approx"])
            for f in ("quality_checks.json", "segments.csv", "experiment_results.json"):
                self.assertTrue((root / "reports" / f).exists(), f)

    def test_orphan_event_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generate(200, seed=42, output_dir=root)
            with sqlite3.connect(root / "saas.db") as conn:
                conn.execute("""INSERT INTO events (event_id, user_id, event_at, event_name)
                                VALUES (999999, 'missing_user', '2026-01-01T12:00:00+00:00', 'signup')""")
            with self.assertRaisesRegex(ValueError, "Data-quality checks failed"):
                analyze(root / "saas.db", root / "reports")

    def test_event_flag_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generate(200, seed=12, output_dir=root)
            with sqlite3.connect(root / "saas.db") as conn:
                conn.execute("UPDATE users SET returned_d28 = 1 - returned_d28 WHERE user_id = 'u000001'")
            with self.assertRaisesRegex(ValueError, "Data-quality checks failed"):
                analyze(root / "saas.db", root / "reports")


if __name__ == "__main__":
    unittest.main()
