# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/QIKVRT_RECURSIVE_EXECUTION_ACCELERATION_V1.json"
DOC = ROOT / "docs/architecture/QIKVRT_RECURSIVE_EXECUTION_ACCELERATION_V1.md"
CONTEXT = ROOT / "AI_CONTEXT.json"
ADOPTION = ROOT / "state/architecture/QIKVRT_RECURSIVE_EXECUTION_ACCELERATION_V1.json"
MARKER = "QIKVRT_RECURSIVE_EXECUTION_ACCELERATION_V1"

SURFACES = [
    "AGENTS.md",
    "next/AI",
    "spec/temdd/TEMDD_NORMATIVE_CORE_V1.md",
    "docs/MESH_SELF_EXPLANATION_AND_DELIVERY.md",
    "docs/architecture/QIKVRT_REAL_MESH_V1.md",
    "docs/terminal/QIKVRT_CLOUD_TRANSPUTER_MATERIALIZATION_V1.md",
    "docs/terminal/FIREFOX_PROXY_DELEGATION_BRIDGE_V1.md",
]

class RecursiveExecutionAccelerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.context = json.loads(CONTEXT.read_text(encoding="utf-8"))
        cls.adoption = json.loads(ADOPTION.read_text(encoding="utf-8"))

    def test_canonical_chain_and_non_equivalences(self):
        self.assertEqual(
            self.policy["canonical_chain"],
            ["COMPILE","BIND","RESOLVE","EXECUTE","TEST","OBSERVE","READBACK","ACCEPT","EFFECT_ACK_DONE"],
        )
        values = set(self.policy["mandatory_non_equivalences"])
        self.assertIn("ACTION_REQUIRED(0 jobs) != JOBS_EXECUTED", values)
        self.assertIn("FAIL_CLOSED != GLOBAL_IDLE", values)
        self.assertIn("TRANSPORT_ACK != EFFECT_ACK", values)
        self.assertFalse(self.policy["effect_boundary"]["predecessor_evidence_transfer"])
        self.assertFalse(self.policy["effect_boundary"]["global_idle_implied"])

    def test_required_read_order_propagates_policy(self):
        order = self.context["required_read_order"]
        self.assertIn("policy/QIKVRT_RECURSIVE_EXECUTION_ACCELERATION_V1.json", order)
        self.assertIn("docs/architecture/QIKVRT_RECURSIVE_EXECUTION_ACCELERATION_V1.md", order)
        self.assertIn("state/architecture/QIKVRT_RECURSIVE_EXECUTION_ACCELERATION_V1.json", order)
        self.assertTrue(self.context["recursive_execution_acceleration"]["required_for_conforming_nodes"])

    def test_explicit_architecture_interfaces_bind_policy(self):
        for relative in SURFACES:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(MARKER, text, relative)

    def test_mesh_machine_contract_preserves_acceleration_semantics(self):
        mesh = json.loads((ROOT / "policy/MESH_SELF_EXPLANATION_V1.json").read_text(encoding="utf-8"))
        preserved = set(mesh["mesh_interoperability"]["must_preserve"])
        for item in (
            "successor_rebinding",
            "causal_blocker_recursion",
            "independent_progress",
            "conflicting_writer_serialization",
            "fresh_effect_readback",
        ):
            self.assertIn(item, preserved)

    def test_adoption_does_not_self_certify_main_or_done(self):
        self.assertFalse(self.adoption["main_adoption"])
        self.assertFalse(self.adoption["repository_effect_ack_done"])
        self.assertFalse(self.adoption["predecessor_evidence_transfer"])

if __name__ == "__main__":
    unittest.main()
