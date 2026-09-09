import json
import unittest
from pathlib import Path

from tools.qikvrt_zero_bug import evaluate, event_ingress_check, self_check


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "ZERO_BUG_CONTINUOUS_V1.json"
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_zero_bug_continuous.yml"


class ZeroBugContinuousTests(unittest.TestCase):
    def good(self):
        return {
            "exact_head_and_tree_bound": True,
            "known_deterministic_defects": 0,
            "repository_integrity_verifies": True,
            "bound_deterministic_gate_bundle_verifies": True,
            "repository_writer_lease_contract_verifies": True,
            "stale_evidence_reuse": 0,
            "registered_improvers_only": True,
            "reobserve_after_every_mutation": True,
            "full_tracked_tree_sha256_bound": True,
        }

    def test_self_check_preserves_hold_after_mutation(self):
        result = self_check()
        self.assertTrue(result["complete"])
        self.assertEqual(result["after_mutation"], "HOLD_UNVERIFIED")
        self.assertEqual(result["after_fresh_local_exact_head_success"], "ZERO_KNOWN_DETERMINISTIC_BUGS_LOCAL")
        self.assertFalse(result["later_is_better"])
        self.assertEqual(result["arbitrary_unregistered_self_modification"], "HOLD")
        self.assertEqual(result["registered_improvers"], ["integrity_trio_materializer"])
        self.assertEqual(result["bit_audit_algorithm"], "sha256")
        self.assertEqual(result["event_ingress_mode"], "EXACT_NATIVE_REPOSITORY_EVENT_ONLY")
        self.assertTrue(result["event_ingress_native_only"])
        self.assertIsNone(result["event_ingress_reason"])

    def test_zero_bug_workflow_accepts_only_native_event_ingress(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        ingress = policy["base_algorithm"]["event_ingress"]
        self.assertEqual(ingress["workflow_path"], ".github/workflows/qikvrt_zero_bug_continuous.yml")
        self.assertEqual(
            ingress["accepted_sources"],
            ["pull_request", "push", "DIRECT_AUTHORIZED_REQUEST"],
        )
        self.assertEqual(
            ingress["forbidden_sources"],
            [
                "schedule",
                "workflow_dispatch",
                "repository_dispatch",
                "api_workflow_dispatch",
                "polling",
                "retry_without_new_event",
            ],
        )
        self.assertEqual(ingress["no_new_event_state"], "HOLD_UNVERIFIED_AWAIT_NEXT_NATIVE_EVENT")
        self.assertEqual(ingress["synthetic_reentry"], "FORBIDDEN")
        self.assertEqual(ingress["periodic_automation"], "FORBIDDEN")

        workflow = WORKFLOW.read_text(encoding="utf-8").split("permissions:", 1)[0]
        self.assertIn("  pull_request:", workflow)
        self.assertIn("  push:", workflow)
        self.assertIn("types: [opened, reopened, synchronize, ready_for_review]", workflow)
        for forbidden in ("schedule", "workflow_dispatch", "repository_dispatch", "/dispatches", "sleep "):
            self.assertNotIn(forbidden, workflow)
        self.assertTrue(event_ingress_check()["native_only"])

    def test_fresh_local_exact_head_is_local_state_only(self):
        result = evaluate(self.good())
        self.assertEqual(result["state"], "ZERO_KNOWN_DETERMINISTIC_BUGS_LOCAL")
        self.assertTrue(result["platform_promotion_evidence_required"])
        self.assertFalse(result["universal_bug_freedom_claimed"])

    def test_any_known_deterministic_defect_forces_hold(self):
        obs = self.good(); obs["known_deterministic_defects"] = 1
        self.assertEqual(evaluate(obs)["state"], "HOLD_DEFECT_IDENTIFIED")

    def test_stale_evidence_forces_hold(self):
        obs = self.good(); obs["stale_evidence_reuse"] = 1
        self.assertEqual(evaluate(obs)["state"], "HOLD_DEFECT_IDENTIFIED")

    def test_writer_lease_contract_failure_forces_hold(self):
        obs = self.good(); obs["repository_writer_lease_contract_verifies"] = False
        self.assertEqual(evaluate(obs)["state"], "HOLD_DEFECT_IDENTIFIED")

    def test_missing_reobservation_forces_hold(self):
        obs = self.good(); obs["reobserve_after_every_mutation"] = False
        self.assertEqual(evaluate(obs)["state"], "HOLD_DEFECT_IDENTIFIED")

    def test_missing_full_tree_sha256_forces_hold(self):
        obs = self.good(); obs["full_tracked_tree_sha256_bound"] = False
        self.assertEqual(evaluate(obs)["state"], "HOLD_DEFECT_IDENTIFIED")

    def test_missing_local_gate_bundle_is_incomplete_not_success(self):
        obs = self.good()
        obs["bound_deterministic_gate_bundle_verifies"] = False
        obs["evidence_incomplete"] = True
        self.assertEqual(evaluate(obs)["state"], "HOLD_EVIDENCE_INCOMPLETE")


class RecursiveDebuggingTests(unittest.TestCase):
    def inventory(self):
        return {
            "schema": "qikvrt_recursive_debugging_inventory_v1",
            "subject": {"repository": "Goldkelch/qik-vrt", "base_sha": "a" * 40, "head_sha": "b" * 40, "tree_sha": "c" * 40},
            "scope": "explicitly observed repair scope",
            "inventory_receipt_id": "inventory-readback",
            "inventory_complete": True,
            "work_units": [self.unit("root")],
        }

    def unit(self, key):
        return {"id": key, "original_scope": "original user operation", "observation_receipt_id": key + "-observed", "blocked_by": [], "causes": [], "receipts": {}}

    def close_unit(self, inv, unit):
        from tools.qikvrt_zero_bug import DEBUGGING_STAGES
        previous = unit["observation_receipt_id"]
        for stage, _ in DEBUGGING_STAGES:
            ident = unit["id"] + "-" + stage
            receipt = {"id": ident, "subject": dict(inv["subject"]), "status": "success", "after": previous}
            if stage in {"symptom", "cause"}:
                receipt["effect_receipt_id"] = unit["id"] + "-effect"
            if stage == "cause":
                receipt["mechanism"] = "wrong display-name classification"
            if stage == "regression":
                receipt["test_id"] = "exact predicate regression"
                receipt["red"] = {"id": ident + "-red", "test_id": receipt["test_id"], "status": "failure", "subject": {**inv["subject"], "head_sha": "d" * 40}}
            if stage == "original_flow":
                receipt["scope"] = unit["original_scope"]
            unit["receipts"][stage] = receipt
            previous = ident

    def plan(self, inv):
        from tools.qikvrt_zero_bug import recursive_debugging_plan
        return recursive_debugging_plan(inv)

    def test_unknown_inventory_is_not_zero(self):
        for inv in (None, {}, [], {"inventory_complete": True}):
            self.assertFalse(self.plan(inv)["complete"])

    def test_only_complete_explicit_empty_inventory_can_close(self):
        inv = self.inventory(); inv["work_units"] = []
        self.assertTrue(self.plan(inv)["complete"])
        for flag in (False, "true", 1, None):
            inv["inventory_complete"] = flag
            self.assertFalse(self.plan(inv)["complete"])

    def test_all_four_exact_causal_receipts_required(self):
        inv = self.inventory(); unit = inv["work_units"][0]
        self.close_unit(inv, unit)
        self.assertTrue(self.plan(inv)["complete"])
        for stage, action in (("symptom", "CORRECT_FAILURE"), ("cause", "IDENTIFY_AND_CORRECT_CAUSE"), ("regression", "VERIFY_REGRESSION"), ("original_flow", "REOBSERVE_ORIGINAL_FLOW")):
            old = unit["receipts"].pop(stage)
            self.assertEqual(self.plan(inv)["actions"][0]["next_action"], action)
            unit["receipts"][stage] = old

    def test_symptom_only_does_not_close_cause(self):
        inv = self.inventory(); unit = inv["work_units"][0]
        self.close_unit(inv, unit); unit["receipts"] = {"symptom": unit["receipts"]["symptom"]}
        self.assertEqual(self.plan(inv)["actions"][0]["next_action"], "IDENTIFY_AND_CORRECT_CAUSE")

    def test_green_local_gates_cannot_hide_known_open_inventory(self):
        obs = ZeroBugContinuousTests().good()
        obs["recursive_debugging_inventory"] = self.inventory()
        self.assertEqual(evaluate(obs)["state"], "HOLD_DEFECT_IDENTIFIED")

    def test_absent_history_is_not_completion_even_when_local_gates_green(self):
        result = evaluate(ZeroBugContinuousTests().good())
        self.assertFalse(result["recursive_debugging"]["complete"])
        self.assertFalse(result["local_gate_success_is_repair_completion"])

    def test_every_subject_mutation_invalidates_current_validation(self):
        for key in ("base_sha", "head_sha", "tree_sha", "repository"):
            inv = self.inventory(); self.close_unit(inv, inv["work_units"][0])
            inv["subject"][key] = "other/repository" if key == "repository" else "e" * 40
            self.assertFalse(self.plan(inv)["complete"])
            self.assertEqual(self.plan(inv)["actions"][0]["next_action"], "CORRECT_FAILURE")

    def test_timestamps_do_not_replace_explicit_receipt_edges(self):
        inv = self.inventory(); unit = inv["work_units"][0]; self.close_unit(inv, unit)
        unit["receipts"]["cause"]["after"] = "unrelated"
        unit["receipts"]["cause"]["timestamp"] = "9999-12-31"
        self.assertFalse(self.plan(inv)["complete"])

    def test_cause_mechanism_and_effect_readback_are_required(self):
        for stage, field in (("symptom", "effect_receipt_id"), ("cause", "effect_receipt_id"), ("cause", "mechanism")):
            inv = self.inventory(); unit = inv["work_units"][0]; self.close_unit(inv, unit)
            unit["receipts"][stage].pop(field)
            self.assertFalse(self.plan(inv)["complete"])

    def test_red_and_green_must_be_the_same_test(self):
        inv = self.inventory(); unit = inv["work_units"][0]; self.close_unit(inv, unit)
        unit["receipts"]["regression"]["red"]["test_id"] = "unrelated test"
        self.assertFalse(self.plan(inv)["complete"])

    def test_red_must_have_reproduced_failure(self):
        inv = self.inventory(); unit = inv["work_units"][0]; self.close_unit(inv, unit)
        unit["receipts"]["regression"]["red"]["status"] = "success"
        self.assertFalse(self.plan(inv)["complete"])

    def test_original_user_flow_not_just_isolated_repair_is_required(self):
        inv = self.inventory(); unit = inv["work_units"][0]; self.close_unit(inv, unit)
        unit["receipts"]["original_flow"]["scope"] = "unrelated operation"
        self.assertFalse(self.plan(inv)["complete"])

    def test_cause_children_remain_open_after_parent_symptom_fix(self):
        inv = self.inventory(); root = inv["work_units"][0]; self.close_unit(inv, root)
        child = self.unit("cause"); root["causes"] = ["cause"]; inv["work_units"].append(child)
        actions = {a["work_unit"]: a["next_action"] for a in self.plan(inv)["actions"]}
        self.assertEqual(actions, {"cause": "CORRECT_FAILURE", "root": "HOLD_CAUSE_WORK_UNIT_OPEN"})
        self.close_unit(inv, child); self.assertTrue(self.plan(inv)["complete"])

    def test_external_blocker_does_not_globally_deadlock_independent_work(self):
        inv = self.inventory(); root = inv["work_units"][0]; root["blocked_by"] = ["credential"]
        inv["work_units"] += [self.unit("credential"), self.unit("independent")]
        actions = {a["work_unit"]: a["next_action"] for a in self.plan(inv)["actions"]}
        self.assertEqual(actions["root"], "HOLD_DEPENDENCY_OPEN")
        self.assertEqual(actions["independent"], "CORRECT_FAILURE")

    def test_cycles_do_not_recurse_forever_or_hide_independent_work(self):
        inv = self.inventory(); inv["work_units"][0]["causes"] = ["root"]
        inv["work_units"].append(self.unit("independent"))
        self.assertEqual(len(self.plan(inv)["actions"]), 2)
        self.assertFalse(self.plan(inv)["complete"])

    def test_missing_child_is_unknown_not_closed(self):
        inv = self.inventory(); inv["work_units"][0]["causes"] = ["missing"]
        self.assertIn("MISSING_DEPENDENCY", self.plan(inv)["actions"][0]["next_action"])

    def test_input_order_does_not_create_causal_order(self):
        inv = self.inventory(); inv["work_units"].append(self.unit("other"))
        first = self.plan(inv); inv["work_units"].reverse()
        self.assertEqual(first, self.plan(inv))

    def test_duplicate_identifiers_and_malformed_links_fail_closed(self):
        inv = self.inventory(); inv["work_units"] *= 2
        self.assertFalse(self.plan(inv)["complete"])
        inv = self.inventory(); inv["work_units"][0]["causes"] = "root"
        self.assertFalse(self.plan(inv)["complete"])

    def test_large_acyclic_graph_uses_worklist_not_call_stack(self):
        inv = self.inventory(); inv["work_units"] = [self.unit(str(i)) for i in range(1050)]
        for i, unit in enumerate(inv["work_units"]):
            unit["causes"] = [str(i - 1)] if i else []
        self.assertEqual(len(self.plan(inv)["unresolved"]), 1050)

    def test_work_budget_overflow_is_hold_not_completion(self):
        inv = self.inventory(); inv["work_units"] = [self.unit(str(i)) for i in range(4097)]
        self.assertEqual(self.plan(inv)["state"], "HOLD_INVENTORY_UNVERIFIED")

    def test_planner_does_not_grant_execution_or_external_effect(self):
        result = self.plan(self.inventory())
        self.assertEqual(result["external_effect"], "NONE")
        self.assertEqual(result["maximum_writers_per_subject"], 1)
        self.assertFalse(result["universal_bug_freedom_claimed"])


if __name__ == "__main__":
    unittest.main()
