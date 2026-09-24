# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations
import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("qikvrt_pr_closure_engine", ROOT / "tools/qikvrt_pr_closure_engine.py")
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class ClosureEngineTests(unittest.TestCase):
    def policy(self, mode="NATIVE_PR_MERGE"):
        return {
            "schema": "qikvrt_autonomous_pr_closure_policy_v1",
            "status": "ACTIVE",
            "required_independent_reviewer": "Goldkelch",
            "max_scan_per_run": 8,
            "max_mutations_per_run": 1,
            "required_check": {"name": "test", "integration_id": 15368},
            "repositories": {
                "example/qik-vrt": {"base_branch": "main", "promotion_mode": mode, "role_local_head_required": True, "ruleset_id": 19344903}
            },
        }

    def pr(self, **kw):
        value = {
            "number": 7, "state": "open", "draft": False, "changed_files": 2,
            "mergeable": True, "mergeable_state": "clean", "body": "",
            "user": {"login": "author"}, "node_id": "PR_node",
            "base": {"ref": "main", "sha": "a" * 40},
            "head": {"ref": "feature", "sha": "b" * 40, "repo": {"full_name": "example/qik-vrt"}},
        }
        value.update(kw)
        return value

    def obs(self, **kw):
        value = {
            "current_main_sha": "a" * 40,
            "compare_status": "ahead",
            "check_runs": [{"id": 1, "name": "test", "status": "completed", "conclusion": "success", "completed_at": "2026-09-23T08:00:00Z", "app": {"id": 15368}}],
            "statuses": [{"id": 2, "context": M.TECHNICAL_REVIEW_CONTEXT, "state": "success", "updated_at": "2026-09-23T08:01:00Z"}],
            "reviews": [{"state": "APPROVED", "commit_id": "b" * 40, "submitted_at": "2026-09-23T08:02:00Z", "user": {"login": "Goldkelch"}}],
            "requested_reviewers": [],
        }
        value.update(kw)
        return value

    def cfg(self, mode="NATIVE_PR_MERGE"):
        return M.validate_policy(self.policy(mode), "example/qik-vrt")

    def test_green_exact_head_is_mergeable(self):
        d = M.classify_pr(self.pr(), self.obs(), self.cfg(), "example/qik-vrt")
        self.assertEqual((d["action"], d["head_sha"], d["main_sha"]), ("MERGE", "b" * 40, "a" * 40))

    def test_no_exact_head_review_requests_reviewer(self):
        d = M.classify_pr(self.pr(), self.obs(reviews=[]), self.cfg(), "example/qik-vrt")
        self.assertEqual(d["action"], "REQUEST_REVIEW")

    def test_stale_review_does_not_authorize_merge(self):
        d = M.classify_pr(self.pr(), self.obs(reviews=[{"state": "APPROVED", "commit_id": "c" * 40, "submitted_at": "x", "user": {"login": "Goldkelch"}}]), self.cfg(), "example/qik-vrt")
        self.assertEqual(d["action"], "REQUEST_REVIEW")

    def test_self_review_never_counts(self):
        pr = self.pr(user={"login": "Goldkelch"})
        d = M.classify_pr(pr, self.obs(), self.cfg(), "example/qik-vrt")
        self.assertEqual(d["action"], "REQUEST_REVIEW")

    def test_non_green_gate_waits(self):
        d = M.classify_pr(self.pr(), self.obs(check_runs=[]), self.cfg(), "example/qik-vrt")
        self.assertEqual(d["action"], "WAIT_REQUIRED_CHECK")

    def test_technical_review_is_independent_gate(self):
        d = M.classify_pr(self.pr(), self.obs(statuses=[]), self.cfg(), "example/qik-vrt")
        self.assertEqual(d["action"], "WAIT_TECHNICAL_REVIEW")

    def test_diverged_clean_branch_is_updated_before_any_review(self):
        d = M.classify_pr(self.pr(), self.obs(compare_status="diverged"), self.cfg(), "example/qik-vrt")
        self.assertEqual(d["action"], "UPDATE_BRANCH")

    def test_conflict_is_explicit_and_does_not_invent_repair(self):
        d = M.classify_pr(self.pr(mergeable=False, mergeable_state="dirty"), self.obs(compare_status="diverged"), self.cfg(), "example/qik-vrt")
        self.assertEqual((d["action"], d["reason"]), ("BLOCK_REPAIR_REQUIRED", "MERGE_CONFLICT"))

    def test_already_contained_closes_without_merge(self):
        d = M.classify_pr(self.pr(changed_files=0), self.obs(compare_status="identical"), self.cfg(), "example/qik-vrt")
        self.assertEqual(d["action"], "CLOSE_ALREADY_CONTAINED")

    def test_only_trusted_self_heal_draft_can_be_ready(self):
        trusted = self.pr(draft=True, user={"login": "github-actions[bot]"}, body=M.AUTO_READY_MARKER, head={"ref": "automation/self-heal-abc", "sha": "b" * 40, "repo": {"full_name": "example/qik-vrt"}})
        self.assertEqual(M.classify_pr(trusted, self.obs(), self.cfg(), "example/qik-vrt")["action"], "MARK_READY")
        self.assertEqual(M.classify_pr(self.pr(draft=True), self.obs(), self.cfg(), "example/qik-vrt")["action"], "BLOCK_DRAFT_REQUIRES_OWNER")

    def test_foreign_head_is_never_mutated(self):
        foreign = self.pr(head={"ref": "feature", "sha": "b" * 40, "repo": {"full_name": "other/fork"}})
        self.assertEqual(M.classify_pr(foreign, self.obs(), self.cfg(), "example/qik-vrt")["action"], "BLOCK_NON_ROLE_LOCAL_HEAD")

    def test_mirror_uses_fast_forward_cas_mode(self):
        d = M.classify_pr(self.pr(), self.obs(), self.cfg("FAST_FORWARD_CAS"), "example/qik-vrt")
        self.assertEqual(d["promotion_mode"], "FAST_FORWARD_CAS")

    def test_scan_window_rotates_past_permanent_front_blockers(self):
        rows = [{"number": n} for n in range(1, 25)]
        first, first_offset = M.scan_window(rows, 8, 1)
        second, second_offset = M.scan_window(rows, 8, 2)
        third, third_offset = M.scan_window(rows, 8, 3)
        self.assertEqual(([x["number"] for x in first], first_offset), (list(range(1, 9)), 0))
        self.assertEqual(([x["number"] for x in second], second_offset), (list(range(9, 17)), 8))
        self.assertEqual(([x["number"] for x in third], third_offset), (list(range(17, 25)), 16))

    def test_closure_workflow_is_event_driven_without_scheduler(self):
        workflow = (ROOT / ".github" / "workflows" / "qikvrt_pr_closure_engine.yml").read_text(encoding="utf-8")
        self.assertNotIn("\n  schedule:", workflow)
        self.assertIn("\n  workflow_run:", workflow)
        self.assertIn("\n  push:", workflow)
        self.assertIn("\n  workflow_dispatch:", workflow)



if __name__ == "__main__":
    unittest.main()
