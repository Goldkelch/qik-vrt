import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "REQUEST_OBLIGATION_CLOSURE_V1.json"
COMPLETION = ROOT / "policy" / "EXECUTABLE_ABSTRACTION_COMPLETION_V1.json"
CONTEXT = ROOT / "AI_CONTEXT.json"
AGENTS = ROOT / "AGENTS.md"


class RequestObligationClosureTest(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.completion = json.loads(COMPLETION.read_text(encoding="utf-8"))
        self.context = json.loads(CONTEXT.read_text(encoding="utf-8"))
        self.agents = AGENTS.read_text(encoding="utf-8")

    def test_policy_preserves_originating_obligations(self):
        invariant = self.policy["transition_invariant"]
        self.assertFalse(invariant["originating_obligation_deletion_allowed"])
        self.assertFalse(invariant["intermediate_success_implies_completion"])
        self.assertTrue(invariant["satisfied_requires_exact_readback"])
        self.assertTrue(invariant["blocked_requires_irreducibility_evidence"])

    def test_return_gate_forces_same_run_continuation(self):
        gate = self.policy["return_gate"]
        self.assertEqual(gate["if_authorized_safe_next_action_exists"], "EXECUTE_IN_SAME_RUN")
        self.assertEqual(gate["describe_executable_next_action_instead_of_executing"], "FORBIDDEN")
        self.assertIn("ALL(request_obligations.state == SATISFIED)", gate["formula"])
        self.assertEqual(gate["requested_effect_and_readback"], "DoD = REQUESTED_EFFECT + EXACT_EFFECT_READBACK")

    def test_absence_of_attempt_is_not_a_block(self):
        hold = self.policy["hold_proof"]
        self.assertEqual(hold["absence_of_attempt"], "NOT_A_BLOCK")
        self.assertIn("available_capabilities_examined", hold["required"])
        self.assertIn("why_each_safe_authorized_action_cannot_advance", hold["required"])

    def test_completion_policy_binds_ledger(self):
        self.assertEqual(self.completion["request_obligation_policy"], "policy/REQUEST_OBLIGATION_CLOSURE_V1.json")
        rule = self.completion["completion_rule"]
        self.assertFalse(rule["originating_request_obligation_loss_allowed"])
        self.assertFalse(rule["return_while_authorized_safe_next_action_exists"])
        self.assertTrue(rule["satisfied_obligation_requires_exact_effect_readback"])

    def test_ai_entrypoint_loads_policy_before_work(self):
        order = self.context["required_read_order"]
        self.assertIn("policy/REQUEST_OBLIGATION_CLOSURE_V1.json", order)
        self.assertLess(order.index("policy/REQUEST_OBLIGATION_CLOSURE_V1.json"), order.index("README.md"))
        self.assertTrue(self.context["verification_boundary"]["request_done_requires_all_bound_obligations_discharged"])

    def test_human_contract_matches_machine_contract(self):
        self.assertIn("NO_USER_RETURN_WHILE_AUTHORIZED_NEXT_ACTION_EXISTS", self.agents)
        self.assertIn("DoD = REQUESTED_EFFECT + EXACT_EFFECT_READBACK", self.agents)


if __name__ == "__main__":
    unittest.main()
