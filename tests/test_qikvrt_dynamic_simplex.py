import unittest

from tools.qikvrt_dynamic_simplex import decide


def snap(**overrides):
    value = {
        "schema": "qikvrt_dynamic_simplex_snapshot_v1",
        "target_generation": "g1",
        "observed_generation": "g1",
        "objective": {"latency": 1.0, "risk": 4.0},
        "current_vertex": "A",
        "vertices": {
            "A": {"metrics": {"latency": 5, "risk": 2}, "feasible": True, "evidence_bound": True},
            "B": {"metrics": {"latency": 4, "risk": 1}, "feasible": True, "evidence_bound": True},
            "C": {"metrics": {"latency": 1, "risk": 9}, "feasible": True, "evidence_bound": True},
        },
        "edges": [["A", "B"], ["A", "C"]],
    }
    value.update(overrides)
    return value


class DynamicSimplexTests(unittest.TestCase):
    def test_strict_improvement_pivots_deterministically(self):
        d = decide(snap())
        self.assertEqual(d.action, "PIVOT")
        self.assertEqual(d.to_vertex, "B")
        self.assertLess(d.objective_after, d.objective_before)

    def test_moving_target_requires_reobservation(self):
        d = decide(snap(observed_generation="g0"))
        self.assertEqual((d.action, d.reason), ("REOBSERVE", "MOVING_TARGET_DRIFT"))

    def test_unbound_current_evidence_holds(self):
        s = snap()
        s["vertices"]["A"]["evidence_bound"] = False
        self.assertEqual(decide(s).action, "HOLD")

    def test_unbound_or_infeasible_neighbor_is_not_selected(self):
        s = snap()
        s["vertices"]["B"]["evidence_bound"] = False
        self.assertEqual(decide(s).action, "NOOP")

    def test_fixpoint_is_noop(self):
        s = snap()
        s["vertices"]["B"]["metrics"] = {"latency": 20, "risk": 20}
        self.assertEqual(decide(s).action, "NOOP")

    def test_schema_is_fail_closed(self):
        s = snap()
        s["extra"] = True
        with self.assertRaises(ValueError):
            decide(s)


if __name__ == "__main__":
    unittest.main()
