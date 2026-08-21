import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.qikvrt_monitor_sampling import evaluate


class MonitorSamplingTests(unittest.TestCase):
    def test_below_nyquist_holds(self):
        r = evaluate(source_max_hz=10.0, sample_hz=19.9, event_driven=False)
        self.assertFalse(r.admitted)
        self.assertEqual(r.disposition, "HOLD_BELOW_NYQUIST")

    def test_exact_nyquist_is_admitted_but_not_guarded(self):
        r = evaluate(source_max_hz=10.0, sample_hz=20.0, event_driven=False)
        self.assertTrue(r.admitted)
        self.assertTrue(r.completeness_claim_allowed)
        self.assertEqual(r.disposition, "NYQUIST_BOUNDARY_MET_GUARD_MARGIN_NOT_MET")

    def test_guard_margin(self):
        r = evaluate(source_max_hz=10.0, sample_hz=25.0, event_driven=False)
        self.assertTrue(r.admitted)
        self.assertEqual(r.disposition, "ADMITTED_WITH_GUARD_MARGIN")

    def test_unknown_bandwidth_polling_fails_closed(self):
        r = evaluate(source_max_hz=None, sample_hz=1000.0, event_driven=False)
        self.assertFalse(r.admitted)
        self.assertFalse(r.completeness_claim_allowed)
        self.assertEqual(r.disposition, "HOLD_SAMPLING_BOUND_UNKNOWN")

    def test_unknown_bandwidth_event_driven_admitted_without_nyquist_claim(self):
        r = evaluate(source_max_hz=None, sample_hz=None, event_driven=True)
        self.assertTrue(r.admitted)
        self.assertFalse(r.completeness_claim_allowed)
        self.assertIn("GAP_REOBSERVE_REQUIRED", r.disposition)

    def test_policy_is_global_and_preserves_boundaries(self):
        policy = json.loads((ROOT / "policy/UNIVERSAL_MONITOR_SAMPLING_V1.json").read_text())
        self.assertIn("EVERY_FUTURE_MESH_NODE", policy["applies_to"])
        self.assertIn("BROWSER_TERMINAL", policy["applies_to"])
        self.assertIn("REFLEXIVE_WATCHDOG", policy["applies_to"])
        self.assertIn("NO_DECLARED_BANDLIMIT != NYQUIST_COMPLETENESS", policy["invariants"])
        self.assertFalse(policy["effect_boundary"]["sampling_success_implies_causality"])
        self.assertFalse(policy["effect_boundary"]["sampling_success_implies_effect_ack"])

    def test_cli_fail_closed(self):
        p = subprocess.run([sys.executable, str(ROOT / "tools/qikvrt_monitor_sampling.py"), "--sample-hz", "100"], text=True, capture_output=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("HOLD_SAMPLING_BOUND_UNKNOWN", p.stdout)


if __name__ == "__main__":
    unittest.main()
