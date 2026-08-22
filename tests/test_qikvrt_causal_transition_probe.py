import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tools" / "qikvrt_causal_transition_probe.py"


def case(*, current_quality=1, expected_quality=2, observed_quality=2, cause="past-0"):
    return {
        "past": {"id": "past-0", "quality": 1, "logical_time": 0},
        "current": {"id": "now-1", "quality": current_quality, "logical_time": 1},
        "expected": {"id": "future-2", "quality": expected_quality, "logical_time": 2},
        "observed": {"id": "observed-2", "quality": observed_quality, "logical_time": 2},
        "cause": cause,
        "objective": "HIGHER_QUALITY_IS_BETTER",
    }


class CausalTransitionProbeTests(unittest.TestCase):
    def run_probe(self, payload):
        return subprocess.run(
            [sys.executable, str(PROBE)],
            input=json.dumps(payload), text=True, capture_output=True, cwd=ROOT
        )

    def test_expected_future_is_reobserved_and_improvement_is_evidenced(self):
        r = self.run_probe(case(observed_quality=2))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertTrue(out["expected_equals_observed"])
        self.assertTrue(out["improved"])
        self.assertEqual(out["classification"], "IMPROVEMENT_EVIDENCED")
        self.assertFalse(out["later_implies_better"])

    def test_later_without_change_is_not_better(self):
        r = self.run_probe(case(expected_quality=2, observed_quality=1))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertTrue(out["later"])
        self.assertFalse(out["changed"])
        self.assertFalse(out["improved"])
        self.assertFalse(out["expected_equals_observed"])
        self.assertEqual(out["classification"], "UNCHANGED")
        self.assertFalse(out["later_implies_better"])

    def test_later_changed_state_can_be_worse(self):
        r = self.run_probe(case(current_quality=1, expected_quality=2, observed_quality=0))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertTrue(out["later"])
        self.assertTrue(out["changed"])
        self.assertTrue(out["degraded"])
        self.assertFalse(out["improved"])
        self.assertEqual(out["classification"], "CHANGED_DEGRADED")

    def test_missing_causal_binding_holds(self):
        r = self.run_probe(case(cause=""))
        self.assertEqual(r.returncode, 2)
        out = json.loads(r.stdout)
        self.assertEqual(out, {"reason": "CAUSE_NOT_BOUND", "status": "HOLD"})

    def test_missing_objective_holds(self):
        payload = case()
        payload["objective"] = ""
        r = self.run_probe(payload)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stdout)["reason"], "OBJECTIVE_NOT_BOUND")


if __name__ == "__main__":
    unittest.main()
