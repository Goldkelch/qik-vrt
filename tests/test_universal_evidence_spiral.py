# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "qikvrt_universal_evidence_spiral.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("qikvrt_universal_evidence_spiral", TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load universal resolver")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UniversalEvidenceSpiralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.m = load_tool()

    def subject(self, identity: str = "example-problem") -> dict[str, str]:
        return {"repository": "Goldkelch/qik-vrt", "identity": identity, "head": "a" * 40, "tree": "b" * 40}

    def move(self, **overrides):
        value = {"id": "repair", "objective": "DETERMINISTIC_CORRECTNESS", "action": "apply bounded repair", "authority": "REPOSITORY_INTERNAL", "expected_readback": "same-subject regression becomes green", "mutating": True}
        value.update(overrides); return value

    def problem(self, identity: str = "example-problem", **overrides):
        value = {"subject": self.subject(identity)}; value.update(overrides); return value

    def test_missing_exact_subject_reobserves(self) -> None:
        receipt = self.m.resolve({"subject": {"repository": "Goldkelch/qik-vrt"}})
        self.assertEqual(receipt["state"], "REOBSERVE"); self.assertEqual(receipt["d0"], 2)

    def test_stale_subject_reobserves_before_mutation(self) -> None:
        receipt = self.m.resolve({"subject": self.subject(), "subject_state": "STALE", "candidate_moves": [self.move()]})
        self.assertEqual(receipt["state"], "REOBSERVE"); self.assertIsNone(receipt["executed_move"])

    def test_unresolved_dependency_holds(self) -> None:
        receipt = self.m.resolve({"subject": self.subject(), "dependencies": [{"id": "review", "state": "OPEN"}], "candidate_moves": [self.move()]})
        self.assertEqual(receipt["state"], "HOLD"); self.assertEqual(receipt["dependencies"], ["review"])

    def test_predecessor_evidence_transfer_is_rejected(self) -> None:
        receipt = self.m.resolve({"subject": self.subject(), "candidate_moves": [self.move(transfers_predecessor_evidence=True)]})
        self.assertEqual(receipt["state"], "NOOP"); self.assertEqual(receipt["rejected_moves"][0]["reason"], "PREDECESSOR_EVIDENCE_TRANSFER_FORBIDDEN")

    def test_unreadback_external_claim_is_rejected(self) -> None:
        receipt = self.m.resolve({"subject": self.subject(), "candidate_moves": [self.move(claims_without_readback=["PUBLICATION"])]})
        self.assertEqual(receipt["state"], "NOOP"); self.assertEqual(receipt["rejected_moves"][0]["reason"], "UNREADBACK_EXTERNAL_OR_TERMINAL_CLAIM_FORBIDDEN")

    def test_authority_boundary_requests_authority(self) -> None:
        receipt = self.m.resolve({"subject": self.subject(), "candidate_moves": [self.move(authority="ZENODO_PRODUCTION")]})
        self.assertEqual(receipt["state"], "REQUEST_AUTHORITY"); self.assertEqual(receipt["requested_authority"], "ZENODO_PRODUCTION")

    def test_highest_objective_wins_deterministically(self) -> None:
        receipt = self.m.resolve({"subject": self.subject(), "candidate_moves": [self.move(id="observability", objective="TESTABILITY_AND_OBSERVABILITY", risk=0), self.move(id="correctness", objective="DETERMINISTIC_CORRECTNESS", risk=10)]})
        self.assertEqual(receipt["state"], "ACTION"); self.assertEqual(receipt["selected_move"], "correctness"); self.assertEqual(receipt["mutation_budget"], 1)

    def test_activity_only_noise_does_not_change_causal_fingerprint(self) -> None:
        a = {"subject": self.subject(), "run_count": 1, "updated_at": "t1"}; b = {"subject": self.subject(), "run_count": 999, "updated_at": "t2"}
        self.assertEqual(self.m.causal_fingerprint(a), self.m.causal_fingerprint(b))

    def test_recursive_depth_and_breadth_are_deterministic(self) -> None:
        root = self.problem("root", subproblems=[self.problem("b"), self.problem("a", subproblems=[self.problem("a-child")])])
        receipt = self.m.recursive_resolve(root, max_depth=8, max_nodes=32)
        identities = [(node.get("receipt") or {}).get("subject", {}).get("identity") for node in receipt["receipts"] if node.get("receipt")]
        self.assertEqual(identities, ["root", "a", "b", "a-child"]); self.assertEqual(receipt["nodes_observed"], 4); self.assertEqual(receipt["closure"], "LOCAL_FIXPOINT")

    def test_recursive_cycle_is_deduplicated(self) -> None:
        a = self.problem("a"); root = self.problem("root", subproblems=[a, a])
        receipt = self.m.recursive_resolve(root, max_depth=8, max_nodes=32)
        reasons = [node.get("reason") for node in receipt["receipts"]]
        self.assertIn("CAUSAL_CYCLE_DEDUPLICATED", reasons); self.assertEqual(receipt["nodes_observed"], 2)

    def test_recursive_depth_limit_holds_instead_of_claiming_finality(self) -> None:
        root = self.problem("root", subproblems=[self.problem("child", subproblems=[self.problem("grandchild")])])
        receipt = self.m.recursive_resolve(root, max_depth=1, max_nodes=32)
        self.assertEqual(receipt["closure"], "OPEN_FRONTIER"); self.assertIn("MAX_DEPTH_REACHED", receipt["stop_reasons"]); self.assertFalse(receipt["global_finality_claimed"])

    def test_recursive_node_limit_is_fail_closed(self) -> None:
        root = self.problem("root", subproblems=[self.problem("a"), self.problem("b")])
        receipt = self.m.recursive_resolve(root, max_depth=8, max_nodes=2)
        self.assertEqual(receipt["closure"], "OPEN_FRONTIER"); self.assertIn("MAX_NODES_REACHED", receipt["stop_reasons"])

    def test_recursive_action_keeps_frontier_open(self) -> None:
        root = self.problem("root", candidate_moves=[self.move()]); receipt = self.m.recursive_resolve(root)
        self.assertEqual(receipt["closure"], "OPEN_FRONTIER"); self.assertEqual(receipt["receipts"][0]["receipt"]["state"], "ACTION")


if __name__ == "__main__":
    unittest.main()
