"""Regression tests for synthetic dataset and statistical pipeline."""
import csv
import tempfile
import unittest
from pathlib import Path

from saas_analytics.analyze import analyze, compare_binary
from saas_analytics.simulate import generate


class PipelineTest(unittest.TestCase):
    def test_reproducibility_and_integrity(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            da, db = Path(a), Path(b)
            generate(200, 12, da)
            generate(200, 12, db)
            self.assertEqual((da / "users.csv").read_bytes(), (db / "users.csv").read_bytes())
            self.assertEqual((da / "events.csv").read_bytes(), (db / "events.csv").read_bytes())
            with (da / "users.csv").open(newline="") as f:
                users = list(csv.DictReader(f))
            self.assertEqual(len(users), 200)
            self.assertEqual(len({u["user_id"] for u in users}), 200)
            self.assertTrue(all(u["variant"] in {"control", "treatment"} for u in users))
            self.assertTrue(all(int(u["activated_d7"]) <= int(u["integration_connected"]) for u in users))
            self.assertTrue(all(int(u["integration_connected"]) <= int(u["workspace_created"]) for u in users))
            result = analyze(da / "saas.db", da / "reports")
            self.assertEqual(result["users_total"], 200)
            self.assertTrue((da / "reports" / "summary.md").exists())

    def test_binary_effect(self):
        result = compare_binary(60, 100, 50, 100)
        self.assertAlmostEqual(result["absolute_lift_pp"], 10.0)
        self.assertLess(result["p_value_two_sided"], 1)
        self.assertGreater(result["confidence_interval_95_pp"][1], 0)

    def test_small_n_rejected(self):
        with self.assertRaises(ValueError):
            generate(1, 12, Path("unused"))


if __name__ == "__main__":
    unittest.main()
