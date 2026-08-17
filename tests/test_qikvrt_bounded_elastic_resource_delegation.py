import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "state/autonomy/BOUNDED_ELASTIC_RESOURCE_DELEGATION_V1.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_bounded_elastic_observers.yml"
PLANNER = ROOT / "tools/qikvrt_elastic_resource_planner.py"


class BoundedElasticResourceDelegationTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        spec = importlib.util.spec_from_file_location("planner", PLANNER)
        self.planner = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(self.planner)

    def test_single_productive_writer_is_invariant(self):
        self.assertEqual(self.policy["serialization"]["productive_writer_limit"], 1)
        self.assertTrue(self.policy["serialization"]["competing_productive_writer_forbidden"])
        self.assertTrue(self.policy["serialization"]["productive_writer_requires_fresh_terminal_admission_clear"])

    def test_parallelism_is_read_only_and_bounded(self):
        plan = self.planner.build_plan(99)
        self.assertLessEqual(plan["observer_lanes"], 8)
        self.assertEqual(plan["productive_writer_limit"], 1)
        self.assertTrue(plan["constraints"]["read_only_parallel_lanes"])
        self.assertFalse(plan["constraints"]["external_effect_authorization_implied"])

    def test_planner_reduction_is_deterministic(self):
        self.assertEqual(self.planner.build_plan(4), self.planner.build_plan(4))

    def test_security_boundaries_are_explicit(self):
        security = self.policy["security"]
        for key in (
            "credential_escalation_forbidden",
            "permission_escalation_forbidden",
            "platform_quota_bypass_forbidden",
            "foreign_system_use_without_authorization_forbidden",
        ):
            self.assertTrue(security[key])

    def test_failed_gate_cannot_be_masked(self):
        gates = self.policy["gate_preservation"]
        self.assertTrue(gates["failed_gate_may_not_be_masked_by_parallel_success"])
        self.assertTrue(gates["exact_head_required"])
        self.assertTrue(gates["review_required"])

    def test_workflow_binds_and_verifies_exact_source_head(self):
        source_ref = "ref: ${{ github.event.pull_request.head.sha || github.sha }}"
        source_env = "EXPECTED_HEAD: ${{ github.event.pull_request.head.sha || github.sha }}"
        self.assertEqual(self.workflow.count(source_ref), 2)
        self.assertEqual(self.workflow.count("name: Verify exact source head checkout"), 2)
        self.assertEqual(self.workflow.count(source_env), 2)
        self.assertEqual(self.workflow.count('test "$actual" = "$EXPECTED_HEAD"'), 2)
        self.assertIn('head="$(git rev-parse --verify HEAD^{commit})"', self.workflow)

    def test_workflow_has_parallel_matrix_but_no_write_permission(self):
        self.assertIn("max-parallel: 8", self.workflow)
        self.assertIn("matrix:", self.workflow)
        self.assertIn("permissions:\n  contents: read", self.workflow)
        self.assertNotIn("contents: write", self.workflow)
        self.assertNotIn("pull-requests: write", self.workflow)
        self.assertNotIn("actions: write", self.workflow)
        self.assertIn("persist-credentials: false", self.workflow)


if __name__ == "__main__":
    unittest.main()
