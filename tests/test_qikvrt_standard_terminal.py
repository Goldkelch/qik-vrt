# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import unittest
from tools import qikvrt_standard_terminal as terminal

HEAD = "1" * 40
TREE = "2" * 40


def receipt(**overrides):
    value = {
        "repository": "Goldkelch/qik-vrt",
        "head_sha": HEAD,
        "tree_sha": TREE,
        "semantic_fingerprint": "a" * 64,
        "state": "QUIESCENT_OBSERVATION",
        "disposition": "OBSERVE",
        "first_blocker": None,
        "productive_edge": "KEEP_REFLEXIVE_OBSERVER_FRESH",
        "observations": {"untrusted_terminal_runs": []},
        "gatewatch": {"executed_failures": []},
    }
    value.update(overrides)
    return value


class StandardTerminalTests(unittest.TestCase):
    def test_contract_covers_mesh_node_and_internal_loci(self):
        contract = terminal.load_contract()
        scopes = {item["scope"] for item in contract["architectural_loci"]}
        self.assertEqual({"MESH_BOUNDARY", "MESH_NODE_BOUNDARY", "MESH_NODE_INTERNAL"}, scopes)
        self.assertGreaterEqual(len(contract["architectural_loci"]), 12)

    def test_precedence_keeps_integrity_defect_separate_from_expected_hold(self):
        self.assertEqual(
            "INTEGRITY_PROJECTION_DEFECT",
            terminal.classify({"expected_semantic_hold": True, "integrity_projection_defect": True}),
        )

    def test_platform_barrier_is_not_success(self):
        value = receipt(
            state="UNTRUSTED_EXECUTION_GAP",
            disposition="HOLD",
            observations={"untrusted_terminal_runs": [{"conclusion": "action_required", "job_count": 0}]},
        )
        outward, inward = terminal.project_watchdog(value)
        self.assertEqual("PLATFORM_PRE_JOB_BARRIER", inward["aggregate"]["classification"])
        self.assertTrue(inward["aggregate"]["blocks_productive_progress"])
        self.assertFalse(inward["aggregate"]["admit_productive_writer"])
        self.assertFalse(any(event["semantic_truth_authority"] for event in outward["events"]))

    def test_outward_and_inward_share_deterministic_event_ids(self):
        outward, inward = terminal.project_watchdog(receipt())
        self.assertEqual(
            [item["event_id"] for item in outward["events"]],
            [item["event_id"] for item in inward["events"]],
        )
        outward2, inward2 = terminal.project_watchdog(receipt(), inward)
        self.assertEqual(outward["events"], outward2["events"])
        self.assertEqual("REFLEXIVE_STABLE", inward2["reflexive_relation"])

    def test_stale_writer_holds_productive_writer_but_keeps_observer_alive(self):
        value = receipt(state="PREEMPTIVE_HOLD_STALE_WRITER_LEASE", disposition="HOLD")
        _outward, inward = terminal.project_watchdog(value)
        writer = terminal.verify_inward(inward, expected_head=HEAD, expected_tree=TREE, observer=False)
        observer = terminal.verify_inward(inward, expected_head=HEAD, expected_tree=TREE, observer=True)
        self.assertEqual("HOLD", writer["state"])
        self.assertEqual("ADMIT", observer["state"])

    def test_exact_binding_mismatch_fails_closed(self):
        _outward, inward = terminal.project_watchdog(receipt())
        with self.assertRaises(terminal.TerminalBlock):
            terminal.verify_inward(inward, expected_head="3" * 40, expected_tree=TREE, observer=True)


if __name__ == "__main__":
    unittest.main()
