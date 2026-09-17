# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""One tested inventory for all serialized main or candidate repository writers."""

from __future__ import annotations

import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CONTRACT = ROOT / "state" / "autonomy" / "WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
ZERO_BUG = ROOT / "policy" / "ZERO_BUG_CONTINUOUS_V1.json"

# This is deliberately scoped: fixed ledger refs and separately-authorized
# external effects are not treated as main/candidate ref writers. Their scopes
# cannot silently join this serialization domain without a contract change.
SERIALIZED_WRITER_PATHS = {
    "Autonomous issue processing": "issue-autonomous-processing.yml",
    "QIK-VRT autonomous bounded self-heal": "qikvrt_autonomous_self_heal.yml",
    "QIK-VRT autonomous draft-PR continuation": "qikvrt_autonomous_pr_continuation.yml",
    "QIKVRT Batch-003 remaining subject disposition": "qikvrt_batch003_remaining_disposition.yml",
    "QIKVRT repository evidence materialization": "qikvrt_batch04_integrity.yml",
    "QIKVRT universal terminal materialization": "qikvrt_universal_terminal_materialize.yml",
    "QIKVRT requested review executor": "qikvrt_requested_review_executor.yml",
}
CONSUMERS = (
    "qikvrt_requested_review_executor.yml",
    "qikvrt_required_review_gate.yml",
    "qikvrt_expected_head_promotion.yml",
)
# Every repository ref push is intentionally enumerated here.  This catches a
# newly introduced mutable-ref writer even when its target is assembled through
# a shell variable rather than spelled as ``main``.
PUSH_COUNTS = {
    "issue-autonomous-processing.yml": 1,
    "publish_ontology_difference_article_zenodo_v3.yml": 1,
    "qikvrt_autonomous_pr_continuation.yml": 1,
    "qikvrt_autonomous_self_heal.yml": 1,
    "qikvrt_batch003_remaining_disposition.yml": 2,
    "qikvrt_batch04_integrity.yml": 2,
    "qikvrt_canonical_temporal_memory_zenodo_publish.yml": 1,
    "qikvrt_escape_stages_integrity.yml": 1,
    "qikvrt_formalization_v2_alpha3_publish.yml": 3,
    "qikvrt_global_completion.yml": 1,
    "qikvrt_physics_bridge_integrity.yml": 1,
    "qikvrt_pr18_integrity_repair.yml": 1,
    "qikvrt_proof_persistence_integrity.yml": 1,
    "qikvrt_relational_time_evidence_sphere_materialize.yml": 1,
    "qikvrt_round_trip_zenodo_publish.yml": 1,
    "qikvrt_survival_connectability_zenodo_publish.yml": 1,
    "qikvrt_universal_terminal_materialize.yml": 1,
}
FIXED_NON_MAIN_PUSH_BRANCHES = {
    "qikvrt_canonical_temporal_memory_zenodo_publish.yml": (
        "publication/canonical-temporal-memory-effect-ack-v1"
    ),
    "qikvrt_round_trip_zenodo_publish.yml": "publication/round-trip-canonical-v1-8db8780b",
    "qikvrt_survival_connectability_zenodo_publish.yml": "publication/survival-anschlussfaehig-v1",
}
FIXED_LITERAL_NON_MAIN_PUSHES = {
    "publish_ontology_difference_article_zenodo_v3.yml": "publication/ontology-difference-reverse-engineering",
    "qikvrt_escape_stages_integrity.yml": "agent/escape-stages-batch06",
    "qikvrt_physics_bridge_integrity.yml": "agent/formalization-v2-physics-bridge-01",
    "qikvrt_pr18_integrity_repair.yml": "infra/live-status-default-branch",
    "qikvrt_proof_persistence_integrity.yml": "agent/proof-persistence-batch05",
}


def workflow_name(path: pathlib.Path) -> str:
    match = re.search(r"^name:\s*(.+?)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)
    if match is None:
        raise AssertionError(f"workflow has no name: {path}")
    return match.group(1).strip().strip("'\"")


def embedded_writer_lists(text: str) -> list[list[str]]:
    matches = re.findall(
        r"(?:MESH_REVIEW_)?WRITER_WORKFLOWS_JSON:\s*>-\s*\n\s*(\[[^\n]+\])",
        text,
    )
    return [json.loads(value) for value in matches]


class WriterInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expected = list(SERIALIZED_WRITER_PATHS)
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.zero_bug = json.loads(ZERO_BUG.read_text(encoding="utf-8"))

    def test_one_serialized_inventory_binds_contract_policy_and_consumers(self) -> None:
        writers = self.contract["dispatch_policy"]["writer_workflow_names"]
        self.assertEqual(writers, self.expected)
        self.assertEqual(
            self.zero_bug["audit_surface"]["writer_workflows"],
            self.expected,
        )
        self.assertEqual(
            self.contract["executor"]["repository_writer_inventory"],
            "dispatch_policy.writer_workflow_names",
        )
        self.assertEqual(
            self.contract["executor"]["stateful_writes"],
            "EXECUTOR_ACTION_ARTIFACTS_ONLY",
        )
        for workflow in CONSUMERS:
            lists = embedded_writer_lists((WORKFLOWS / workflow).read_text(encoding="utf-8"))
            self.assertTrue(lists, workflow)
            self.assertTrue(all(value == self.expected for value in lists), workflow)

    def test_every_serialized_writer_is_bound_to_its_exact_workflow_path(self) -> None:
        for expected_name, filename in SERIALIZED_WRITER_PATHS.items():
            self.assertEqual(workflow_name(WORKFLOWS / filename), expected_name)

    def test_direct_main_push_and_automatic_merge_are_repository_wide_forbidden(self) -> None:
        for workflow in sorted(WORKFLOWS.glob("*.yml")):
            text = workflow.read_text(encoding="utf-8")
            self.assertNotIn("git push origin HEAD:main", text, workflow.name)
            self.assertNotRegex(
                text,
                r'git push origin\s+"?HEAD:refs/heads/main"?',
                workflow.name,
            )
            self.assertNotRegex(text, r"(?m)^\s*(?:GH_TOKEN=\S+\s+)?gh\s+pr\s+merge\b", workflow.name)

    def test_every_repository_push_has_an_explicit_nonmain_or_candidate_binding(self) -> None:
        observed = {}
        for workflow in sorted(WORKFLOWS.glob("*.yml")):
            text = workflow.read_text(encoding="utf-8")
            commands = re.findall(r"(?m)^\s*git\s+push\s+(.+)$", text)
            if not commands:
                continue
            self.assertTrue(
                all(command.startswith("origin ") for command in commands),
                f"push must name its remote explicitly: {workflow.name}",
            )
            observed[workflow.name] = len(commands)
        self.assertEqual(observed, PUSH_COUNTS)

        for filename, branch in FIXED_NON_MAIN_PUSH_BRANCHES.items():
            text = (WORKFLOWS / filename).read_text(encoding="utf-8")
            self.assertNotEqual(branch, "main", filename)
            self.assertIn(f"EXPECTED_BRANCH: {branch}", text)
            self.assertIn('test "$GITHUB_REF" = "refs/heads/$EXPECTED_BRANCH"', text)
            self.assertIn('git push origin "HEAD:refs/heads/$EXPECTED_BRANCH"', text)

        for filename, branch in FIXED_LITERAL_NON_MAIN_PUSHES.items():
            text = (WORKFLOWS / filename).read_text(encoding="utf-8")
            self.assertNotEqual(branch, "main", filename)
            self.assertIn(branch, text)
            self.assertIn(f"git push origin HEAD:{branch}", text)

        self_heal = (WORKFLOWS / "qikvrt_autonomous_self_heal.yml").read_text(encoding="utf-8")
        self.assertIn('branch="automation/self-heal-${CANDIDATE_ID:0:24}"', self_heal)
        self.assertIn('git push origin "HEAD:refs/heads/$branch"', self_heal)

        continuation = (WORKFLOWS / "qikvrt_autonomous_pr_continuation.yml").read_text(encoding="utf-8")
        self.assertIn('test "$BASE_REF" = "main"', continuation)
        self.assertIn('test "$HEAD_REF" != "main"', continuation)
        self.assertIn('git push origin "HEAD:refs/heads/${HEAD_REF}"', continuation)

        issue_processor = (WORKFLOWS / "issue-autonomous-processing.yml").read_text(encoding="utf-8")
        self.assertIn('[[ "$number" =~ ^[1-9][0-9]*$ ]]', issue_processor)
        self.assertIn('test "$BRANCH" = "issue-agent/$ISSUE_NUMBER"', issue_processor)
        self.assertIn('git push origin "HEAD:refs/heads/$BRANCH"', issue_processor)

        universal = (WORKFLOWS / "qikvrt_universal_terminal_materialize.yml").read_text(encoding="utf-8")
        self.assertIn('branch="automation/universal-terminal-materialization-${source_head:0:16}"', universal)
        self.assertIn('git push origin "HEAD:refs/heads/$branch"', universal)

        relational = (WORKFLOWS / "qikvrt_relational_time_evidence_sphere_materialize.yml").read_text(encoding="utf-8")
        relational_branch = "publication/2026-08-31-relational-time-evidence-sphere-zenodo-v1"
        self.assertIn(f"TARGET_BRANCH: {relational_branch}", relational)
        self.assertIn(f"github.ref == 'refs/heads/{relational_branch}'", relational)
        self.assertIn('git push origin "HEAD:$TARGET_BRANCH"', relational)

        formalization = (WORKFLOWS / "qikvrt_formalization_v2_alpha3_publish.yml").read_text(encoding="utf-8")
        formalization_branch = "automation/formalization-v2-alpha3-publish-20260724"
        self.assertIn(f"- {formalization_branch}", formalization)
        self.assertIn(
            f"os.environ.get('GITHUB_REF_NAME') != '{formalization_branch}'",
            formalization,
        )
        self.assertEqual(formalization.count('git push origin HEAD:"$GITHUB_REF_NAME"'), 3)

        global_completion = (WORKFLOWS / "qikvrt_global_completion.yml").read_text(encoding="utf-8")
        self.assertIn("agent/global-completion-v1|agent/global-completion-finalize-v1", global_completion)
        self.assertIn('git push origin "HEAD:${GITHUB_REF_NAME}"', global_completion)

        for filename, prefix in (
            ("qikvrt_batch003_remaining_disposition.yml", "automation/batch003-repository-evidence-"),
            ("qikvrt_batch04_integrity.yml", "automation/repository-evidence-"),
        ):
            text = (WORKFLOWS / filename).read_text(encoding="utf-8")
            self.assertIn('if [ "$TARGET_REF" = main ]; then', text)
            self.assertIn(f'candidate_branch="{prefix}${{source_head:0:16}}"', text)
            self.assertIn('git push origin "HEAD:refs/heads/$candidate_branch"', text)
            self.assertIn('git push origin "HEAD:$TARGET_REF"', text)

    def test_every_dynamic_target_ref_writer_has_an_exact_main_candidate_route(self) -> None:
        dynamic = []
        for workflow in sorted(WORKFLOWS.glob("*.yml")):
            text = workflow.read_text(encoding="utf-8")
            if 'git push origin "HEAD:$TARGET_REF"' not in text:
                continue
            dynamic.append(workflow.name)
            self.assertIn(workflow_name(workflow), self.expected)
            self.assertIn('if [ "$TARGET_REF" = main ]; then', text)
            self.assertIn("gh pr create", text)
            self.assertIn("--draft", text)
            self.assertIn("tools/qikvrt_candidate_pr_receipt.py", text)
        self.assertEqual(
            dynamic,
            [
                "qikvrt_batch003_remaining_disposition.yml",
                "qikvrt_batch04_integrity.yml",
            ],
        )

    def test_issue_completion_observer_cannot_mutate_refs_merges_or_schedule_itself(self) -> None:
        text = (WORKFLOWS / "issue-agent-autofinish.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow_name(WORKFLOWS / "issue-agent-autofinish.yml"), "Issue agent completion authority observer")
        self.assertNotIn("schedule:", text)
        self.assertNotIn("git push", text)
        self.assertNotIn("gh pr merge", text)
        self.assertNotIn("gh issue close", text)
        self.assertNotIn("MESH_TOKEN", text)
        self.assertNotIn("Issue agent completion authority observer", self.expected)
        self.assertIn("pull_request_target:", text)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", text)
        self.assertIn("^issue-agent/([1-9][0-9]*)$", text)
        self.assertIn('gh workflow run issue-agent-autofinish.yml', (WORKFLOWS / "issue-autonomous-processing.yml").read_text(encoding="utf-8"))
        self.assertNotIn("gh issue list", text)

    def test_operator_dispatch_only_seed_workers_are_outside_self_heal_and_gatewatch(self) -> None:
        operator_only = self.contract["dispatch_policy"]["operator_dispatch_only_workflows"]
        self.assertTrue(operator_only["outside_self_heal_and_gatewatch"])
        self.assertEqual(operator_only["reason"], "READ_ONLY_ON_DEMAND_ARTIFACT_BUILDERS_NOT_REPAIR_WORK_UNITS")
        expected = {
            "QIKVRT Seed Mesh Audit Build": "qikvrt_seed_mesh_audit_export.yml",
            "QIKVRT Seed Mesh Maintenance": "qikvrt_seed_mesh_maintenance.yml",
            "QIKVRT Seed Node Revalidation": "qikvrt_seed_node_revalidation.yml",
            "QIKVRT Seed Registry Acceptance": "qikvrt_seed_registry_acceptance.yml",
        }
        self.assertEqual(
            {item["workflow_name"]: pathlib.Path(item["workflow_path"]).name for item in operator_only["workflows"]},
            expected,
        )
        automated = {item["workflow_name"] for item in self.contract["dispatch_policy"]["authorized_workflows"]}
        observed = set(self.contract["reflexive_deadlock_prevention"]["gatewatch"]["observed_workflow_names"])
        for name, filename in expected.items():
            text = (WORKFLOWS / filename).read_text(encoding="utf-8")
            self.assertEqual(workflow_name(WORKFLOWS / filename), name)
            self.assertIn("workflow_dispatch:", text)
            self.assertNotIn("workflow_run:", text)
            self.assertNotIn("schedule:", text)
            self.assertNotIn("  push:\n", text)
            self.assertIn("contents: read", text)
            self.assertNotIn(name, automated)
            self.assertNotIn(name, observed)

    def test_platform_monitor_is_the_only_scheduled_workflow(self) -> None:
        scheduled = []
        for workflow in sorted(WORKFLOWS.glob("*.yml")):
            if re.search(r"^  schedule:\s*$", workflow.read_text(encoding="utf-8"), re.MULTILINE):
                scheduled.append(workflow.name)
        self.assertEqual(scheduled, ["qikvrt_reflexive_repository_watchdog.yml"])


if __name__ == "__main__":
    unittest.main()
