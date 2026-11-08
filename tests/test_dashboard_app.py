"""Streamlit smoke checks ensure each dashboard navigation view renders."""
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class DashboardAppTest(unittest.TestCase):
    def test_all_views_render_without_uncaught_exceptions(self):
        app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=90)
        app.run()
        self.assertEqual(len(app.exception), 0, [str(e.message) for e in app.exception])
        self.assertIn("SaaS Onboarding Analytics", [x.value for x in app.title])
        for view in ("Onboarding funnel", "Retention & cohorts", "Experiment lab"):
            app.sidebar.radio[0].set_value(view).run()
            self.assertEqual(len(app.exception), 0, [str(e.message) for e in app.exception])


if __name__ == "__main__":
    unittest.main()
