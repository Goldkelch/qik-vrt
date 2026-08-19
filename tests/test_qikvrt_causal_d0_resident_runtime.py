import io
import json
import unittest

from tools.qikvrt_causal_d0_resident_runtime import (
    HOLD,
    NOOP,
    REOBSERVE,
    REQUEST_AUTHORITY,
    classify,
    process_events,
    productive_effect_allowed,
)


class CausalD0ResidentRuntimeTests(unittest.TestCase):
    def test_four_states(self):
        self.assertEqual(classify({}).d0, NOOP)
        self.assertEqual(classify({"prerequisite_missing": True}).d0, HOLD)
        self.assertEqual(classify({"new_evidence": True}).d0, REOBSERVE)
        self.assertEqual(
            classify({"authority_required": True, "authority_bound": False}).d0,
            REQUEST_AUTHORITY,
        )

    def test_authority_dominates_reobservation_and_hold(self):
        event = {
            "authority_required": True,
            "authority_bound": False,
            "new_evidence": True,
            "prerequisite_missing": True,
        }
        self.assertEqual(classify(event).d0, REQUEST_AUTHORITY)

    def test_reobserve_dominates_hold(self):
        self.assertEqual(
            classify({"new_evidence": True, "prerequisite_missing": True}).d0,
            REOBSERVE,
        )

    def test_productive_effect_requires_noop_and_effect_ack_done(self):
        self.assertTrue(productive_effect_allowed(classify({}), "DONE"))
        self.assertFalse(productive_effect_allowed(classify({}), "PENDING"))
        self.assertFalse(
            productive_effect_allowed(classify({"prerequisite_missing": True}), "DONE")
        )

    def test_one_transition_per_input_event(self):
        source = [
            json.dumps({"prerequisite_missing": True}) + "\n",
            json.dumps({"new_evidence": True}) + "\n",
            json.dumps({"effect_ack": "DONE"}) + "\n",
        ]
        out = io.StringIO()
        self.assertEqual(process_events(source, out), 0)
        receipts = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual([r["decision"]["d0"] for r in receipts], [1, 2, 0])
        self.assertEqual(
            [r["productive_effect_allowed"] for r in receipts], [False, False, True]
        )


if __name__ == "__main__":
    unittest.main()
