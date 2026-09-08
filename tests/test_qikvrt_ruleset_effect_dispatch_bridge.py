# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import ast
from pathlib import Path
import textwrap
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_ruleset_effect_dispatch_bridge.yml"


class RulesetEffectDispatchBridgeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_bridge_is_event_driven_and_exact_upstream_bound(self):
        self.assertIn('"QIKVRT required code-owner review"', self.text)
        self.assertIn('"QIKVRT requested review executor"', self.text)
        self.assertIn("types: [completed]", self.text)
        self.assertNotIn("schedule:", self.text)
        self.assertIn("UPSTREAM_RUN_ID", self.text)
        self.assertIn("qikvrt-required-code-owner-selection-${UPSTREAM_RUN_ID}-CANDIDATE", self.text)
        self.assertIn("qikvrt-mesh-review-selection-${UPSTREAM_RUN_ID}-CANDIDATE", self.text)
        self.assertIn("qikvrt_required_code_owner_review_selection_v1", self.text)
        self.assertIn("qikvrt_requested_review_selection_v1", self.text)
        self.assertIn("UPSTREAM_CANDIDATE_ARTIFACT_MISSING_OR_AMBIGUOUS", self.text)

    def test_requested_review_failure_is_bound_by_workflow_path_not_run_name(self):
        self.assertIn(
            "github.event.workflow_run.path == '.github/workflows/qikvrt_requested_review_executor.yml'",
            self.text,
        )
        self.assertIn('case "$upstream_path" in', self.text)
        self.assertIn('".github/workflows/qikvrt_requested_review_executor.yml")', self.text)
        self.assertNotIn("github.event.workflow_run.name == 'QIKVRT requested review executor'", self.text)
        self.assertNotIn('case "$upstream_name" in', self.text)

    def test_failed_executor_can_supply_selection_but_not_review_receipt(self):
        self.assertIn("upstream_conclusion", self.text)
        self.assertIn("success|failure", self.text)
        self.assertIn("selection_basis", self.text)
        self.assertIn("EXACT_EVENT_OR_DISPATCH", self.text)
        self.assertIn("review_execution", self.text)
        self.assertNotIn("mesh-review/review.json", self.text)
        self.assertNotIn("INVALID_REVIEW_SNAPSHOT", self.text)

    def test_deduplicated_failure_status_is_subject_not_run_url_bound(self):
        self.assertIn("failure: CODE_OWNER_RULE_NOT_ENFORCED", self.text)
        self.assertIn("EXACT_RULESET_BLOCKER_STATUS_MISSING", self.text)
        self.assertNotIn("target_url", self.text)

    def test_bridge_uses_admin_credential_only_to_reach_single_effect_writer(self):
        self.assertIn("GH_TOKEN: ${{ secrets.QIKVRT_RULESET_ADMIN_TOKEN }}", self.text)
        self.assertIn("test -n \"${GH_TOKEN:-}\"", self.text)
        self.assertIn("qikvrt_autonomous_ruleset_effect_loop.yml/dispatches", self.text)
        self.assertIn("expected_head:$head", self.text)
        self.assertNotIn("qikvrt_ruleset_reconcile.py", self.text)
        self.assertNotIn("rulesets/19344903", self.text)
        self.assertNotIn("--method PUT", self.text)
        self.assertNotIn("--method PATCH", self.text)

    def test_no_review_merge_or_publication_effect(self):
        self.assertNotIn("gh pr merge", self.text)
        self.assertNotIn("event=APPROVE", self.text)
        self.assertNotIn("pulls/reviews", self.text)
        self.assertNotIn("zenodo", self.text.lower())
        self.assertNotIn("arxiv", self.text.lower())
        self.assertNotIn("wikipedia", self.text.lower())
        self.assertNotIn("EFFECT_ACK_DONE", self.text)


class NativeReviewWorkflowIdentityContractTest(unittest.TestCase):
    """Exercise the actual workflow guards without executing its API code."""

    @classmethod
    def setUpClass(cls):
        cls.path = ".github/workflows/qikvrt_requested_review_executor.yml"
        text = (ROOT / ".github/workflows/qikvrt_required_review_gate.yml").read_text(encoding="utf-8")
        cls.planner = text.split("  plan-native-account-review:\n", 1)[1].split(
            "  native-account-review-as-goldkelch:\n", 1
        )[0]
        condition = cls.planner.split("    if: >-\n", 1)[1].split("    runs-on:", 1)[0]
        cls.job_guard = compile(" ".join(condition.split()).replace("&&", "and"), "job-guard", "eval")
        source = cls.planner.split('python3 -B - <<\'PY\' > "$root/selection.json"\n', 1)[1]
        source = textwrap.dedent(source.split("          PY\n", 1)[0])
        tree = ast.parse(source)
        guards = [
            node for node in tree.body
            if isinstance(node, ast.If) and any(
                isinstance(child, ast.Constant)
                and child.value == "UPSTREAM_EXECUTOR_PROVENANCE_INVALID"
                for child in ast.walk(node)
            )
        ]
        if len(guards) != 1:
            raise AssertionError("expected one exact upstream provenance guard")
        cls.provenance_guard = compile(ast.Expression(guards[0].test), "provenance-guard", "eval")

    def run_fixture(self):
        return {
            "name": "QIKVRT requested review pr=event head=event fp=event",
            "path": self.path,
            "conclusion": "success",
            "event": "pull_request_target",
            "workflow_id": 123,
            "repository": {"full_name": "Goldkelch/qik-vrt"},
        }

    def job_allowed(self, run, *, ref="refs/heads/main", event_name="workflow_run"):
        github = SimpleNamespace(
            ref=ref, event_name=event_name,
            event=SimpleNamespace(workflow_run=SimpleNamespace(**run)),
        )
        return eval(self.job_guard, {"__builtins__": {}}, {"github": github})

    def provenance_invalid(self, run, *, workflow=None):
        return eval(self.provenance_guard, {"__builtins__": {}}, {
            "run": run,
            "workflow": {"id": 123, "path": self.path} if workflow is None else workflow,
            "trusted_path": self.path,
            "repo": "Goldkelch/qik-vrt",
            "allowed_events": {"pull_request_target", "issue_comment", "workflow_run", "workflow_dispatch"},
        })

    def test_native_planner_ignores_dynamic_display_names(self):
        for name in (
            "QIKVRT requested review executor",
            "QIKVRT requested review pr=event head=event fp=event",
            "QIKVRT requested review pr=1045 head=exact fp=exact",
        ):
            with self.subTest(name=name):
                run = {**self.run_fixture(), "name": name}
                self.assertTrue(self.job_allowed(run))
                self.assertFalse(self.provenance_invalid(run))

    def test_native_job_keeps_trusted_main_success_and_event_boundaries(self):
        run = {**self.run_fixture(), "name": "QIKVRT requested review executor"}
        self.assertFalse(self.job_allowed(run, ref="refs/heads/fix/untrusted"))
        self.assertFalse(self.job_allowed(run, event_name="workflow_dispatch"))
        for conclusion in ("failure", "cancelled", "skipped", None):
            with self.subTest(conclusion=conclusion):
                self.assertFalse(self.job_allowed({**run, "conclusion": conclusion}))
        self.assertFalse(self.job_allowed({**run, "path": ".github/workflows/untrusted.yml"}))

    def test_native_provenance_rejects_spoofed_names_and_wrong_identity(self):
        run = {**self.run_fixture(), "name": "QIKVRT requested review executor"}
        for override in (
            {"path": ".github/workflows/untrusted.yml"},
            {"workflow_id": 999},
            {"repository": {"full_name": "other/qik-vrt"}},
            {"conclusion": "failure"},
            {"event": "push"},
        ):
            with self.subTest(override=override):
                self.assertTrue(self.provenance_invalid({**run, **override}))
        self.assertTrue(self.provenance_invalid(run, workflow={"id": 123, "path": "wrong"}))
        self.assertTrue(self.provenance_invalid(run, workflow={"id": 999, "path": self.path}))

    def test_native_provenance_preserves_exact_followup_events(self):
        for event in ("pull_request_target", "issue_comment", "workflow_run", "workflow_dispatch"):
            with self.subTest(event=event):
                self.assertFalse(self.provenance_invalid({**self.run_fixture(), "event": event}))

    def test_native_planner_has_no_display_name_classification(self):
        self.assertNotIn("github.event.workflow_run.name", self.planner)
        self.assertNotIn("run.get('name')", self.planner)


class ReviewRepairScopeContractTest(unittest.TestCase):
    def test_routing_repair_has_no_parallel_fix_branch_writer(self):
        self.assertFalse(
            (ROOT / ".github/workflows/qikvrt_fix_branch_integrity_materializer.yml").exists(),
            "ROUTING_REPAIR_MUST_NOT_INSTALL_PARALLEL_FIX_BRANCH_WRITER",
        )


    def test_routing_regressions_are_wired_into_exact_head_contract_ci(self):
        workflow = (ROOT / ".github/workflows/qikvrt_requested_review_contract.yml").read_text(encoding="utf-8")
        step = workflow.split("      - name: Verify review cores and decisions\n", 1)[1].split(
            "      - name: Verify event, recovery, identity and promotion bindings\n", 1
        )[0]
        command = step.split("python3 -B -m unittest -v", 1)[1]
        self.assertIn(
            "tests.test_qikvrt_ruleset_effect_dispatch_bridge", command,
            "ROUTING_REGRESSION_MODULE_NOT_EXECUTED",
        )
        for path in (
            ".github/workflows/qikvrt_ruleset_effect_dispatch_bridge.yml",
            ".github/workflows/qikvrt_fix_branch_integrity_materializer.yml",
            "tests/test_qikvrt_ruleset_effect_dispatch_bridge.py",
        ):
            self.assertIn('      - "' + path + '"', workflow)
        self.assertIn('ref: $' + '{{ github.event.pull_request.head.sha || github.sha }}', workflow)
        self.assertIn('persist-credentials: false', workflow)

if __name__ == "__main__":
    unittest.main()
