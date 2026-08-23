# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.qikvrt_autonomous_problem_solver import plan_repair

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_mesh_autonomous_repair.yml"
POLICY = ROOT / "policy/MESH_AUTONOMOUS_DETERMINISTIC_REPAIR_V1.json"


def observation(
    run_id,
    name="QIKVRT CI",
    *,
    status="completed",
    conclusion="action_required",
    jobs_total=0,
    created_at="2026-08-23T00:00:00Z",
):
    return {
        "id": run_id,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "jobs_total": jobs_total,
        "created_at": created_at,
    }


class PlannerTests(unittest.TestCase):
    def test_zero_job_action_required_dispatches_exact_head(self):
        plan = plan_repair([observation(1)], mergeable=True)
        self.assertEqual(plan.d0, 2)
        self.assertEqual(plan.action, "DISPATCH_EXACT_HEAD")
        self.assertFalse(plan.productive_effect)
        self.assertTrue(plan.requires_exact_head_revalidation)

    def test_latest_run_supersedes_stale_zero_job(self):
        plan = plan_repair(
            [
                observation(1),
                observation(
                    2,
                    conclusion="success",
                    jobs_total=1,
                    created_at="2026-08-23T00:01:00Z",
                ),
            ],
            mergeable=True,
        )
        self.assertEqual(plan.action, "NONE")
        self.assertEqual(plan.state, "NOOP")

    def test_conflict_free_stale_base_requests_history_preserving_rebind(self):
        plan = plan_repair([], behind_by=4, mergeable=True)
        self.assertEqual(plan.action, "REBIND_CURRENT_MAIN")
        self.assertTrue(plan.productive_effect)
        self.assertTrue(plan.requires_exact_head_revalidation)

    def test_conflicted_stale_base_requests_authority(self):
        plan = plan_repair([], behind_by=4, mergeable=False)
        self.assertEqual(plan.d0, 3)
        self.assertEqual(plan.state, "REQUEST_AUTHORITY")
        self.assertEqual(plan.action, "NONE")

    def test_recoverable_dispatch_error_can_retry(self):
        plan = plan_repair(
            [],
            exact_head_status="error",
            dispatch_error_is_recoverable=True,
            mergeable=True,
        )
        self.assertEqual(plan.action, "DISPATCH_EXACT_HEAD")
        self.assertEqual(plan.reason, "RECOVERABLE_DISPATCH_ERROR")

    def test_executed_failure_never_blindly_retries(self):
        plan = plan_repair(
            [observation(1, conclusion="failure", jobs_total=1)],
            mergeable=True,
        )
        self.assertEqual(plan.d0, 1)
        self.assertEqual(plan.action, "NONE")
        self.assertEqual(plan.reason, "EXECUTED_FAILURE_REQUIRES_REPAIR_RECIPE")

    def test_integrity_failure_uses_registered_materializer(self):
        plan = plan_repair(
            [observation(1, conclusion="failure", jobs_total=1)],
            first_failure_class="REPOSITORY_INTEGRITY_PROJECTION_DRIFT",
            mergeable=True,
        )
        self.assertEqual(plan.action, "DISPATCH_INTEGRITY_MATERIALIZER")
        self.assertFalse(plan.productive_effect)

    def test_empty_current_head_is_reobserved(self):
        plan = plan_repair([], mergeable=True)
        self.assertEqual(plan.action, "DISPATCH_EXACT_HEAD")
        self.assertEqual(plan.reason, "NO_EXACT_HEAD_OBSERVATION")


class RepositoryContractTests(unittest.TestCase):
    def test_policy_is_bounded_and_truthful(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(
            policy["schema"], "qikvrt_mesh_autonomous_deterministic_repair_v1"
        )
        self.assertEqual(policy["productive_writer_limit"], 1)
        self.assertEqual(policy["max_actions_per_run"], 1)
        self.assertFalse(policy["privileged_controller_executes_candidate_code"])
        self.assertFalse(policy["effect_boundaries"]["merge_authority"])
        self.assertFalse(policy["effect_boundaries"]["review_authority"])
        self.assertFalse(policy["effect_boundaries"]["external_effect_authority"])
        self.assertEqual(
            policy["integrity_trio"],
            [
                "REPOSITORY_FILE_MANIFEST.json",
                "REPOSITORY_FILE_MANIFEST.json.sha256",
                "SHA256SUMS.txt",
            ],
        )

    def test_workflow_has_exact_head_and_writer_guards(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        required = (
            "pull_request_target:",
            "workflow_run:",
            "schedule:",
            "pull-requests: write",
            "cancel-in-progress: false",
            "max_actions_per_run",
            "qikvrt_autonomous_problem_solver.py",
            "DISPATCH_EXACT_HEAD",
            "REBIND_CURRENT_MAIN",
            "DISPATCH_INTEGRITY_MATERIALIZER",
            "git ls-remote --heads origin",
            "pulls/${PR_NUMBER}/update-branch",
            "expected_head_sha",
            "rebind-paths-before.txt",
            "rebind-paths-after.txt",
            "cmp -s",
            "compare/${main_sha}...${new_head}",
            "test \"$live_ref\" = \"$HEAD_SHA\"",
            "qikvrt_autonomous_exact_head_verify",
            "candidate_code_executed_by_controller:false",
            "productive_effect:false",
            "effect_ack:\"NOT_REQUIRED\"",
        )
        for token in required:
            self.assertIn(token, text)
        forbidden = (
            "gh auth setup-git",
            "git merge --no-commit",
            "git checkout -B \"$HEAD_REF\"",
            "git push origin \"HEAD:$HEAD_REF\"",
            "git push --force",
            "git push -f",
            "merge_pull_request",
            "pulls/merge",
            "zenodo",
            "EFFECT_ACK_DONE",
        )
        for token in forbidden:
            self.assertNotIn(token, text)

    def test_cli_emits_canonical_json(self):
        payload = {
            "observations": [observation(1)],
            "exact_head_status": "missing",
            "behind_by": 0,
            "mergeable": True,
        }
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.json"
            output_path = Path(tmp) / "output.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "tools/qikvrt_autonomous_problem_solver.py"),
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(result["action"], "DISPATCH_EXACT_HEAD")
            self.assertEqual(result["external_effect"], "NONE")
            self.assertFalse(result["merge_authority"])


if __name__ == "__main__":
    unittest.main()
