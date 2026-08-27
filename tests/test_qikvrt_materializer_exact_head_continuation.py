from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_materializer_exact_head_continuation.yml"


class MaterializerExactHeadContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_event_is_materializer_workflow_run_only(self) -> None:
        text = self.text
        self.assertIn("workflow_run:", text)
        self.assertIn('"QIKVRT repository evidence materialization"', text)
        self.assertIn("types: [completed]", text)
        self.assertNotIn("schedule:", text)
        self.assertNotIn("pull_request_target:", text)

    def test_ready_and_draft_prs_are_not_artificially_separated(self) -> None:
        text = self.text
        self.assertNotIn("draft ==", text)
        self.assertNotIn("draft !=", text)
        self.assertIn("github.event.workflow_run.head_branch != 'main'", text)
        self.assertIn("github.event.workflow_run.head_repository.full_name == github.repository", text)

    def test_privileged_context_never_checks_out_candidate_bytes(self) -> None:
        text = self.text
        self.assertNotIn("actions/checkout", text)
        self.assertNotIn("git push", text)
        self.assertNotIn("update-branch", text)
        self.assertNotIn("merge_pull_request", text)
        self.assertNotIn("gh pr merge", text)
        self.assertNotIn("gh pr review", text)

    def test_live_head_must_be_direct_canonical_materializer_successor(self) -> None:
        text = self.text
        self.assertIn('test "$parent_count" -eq 1', text)
        self.assertIn('test "$parent_sha" = "$SOURCE_HEAD"', text)
        self.assertIn('test "$commit_message" = "ci: materialize repository evidence"', text)
        self.assertIn('test "$author_login" = "github-actions[bot]"', text)
        self.assertIn('test "$live_head_again" = "$live_head"', text)

    def test_dispatch_is_exact_head_bound(self) -> None:
        text = self.text
        self.assertIn("qikvrt_autonomous_exact_head_verify", text)
        self.assertIn("'pull_request': int('${pr_number}')", text)
        self.assertIn("'head_ref': '${HEAD_REF}'", text)
        self.assertIn("'head_sha': '${live_head}'", text)
        self.assertIn("'source_head_sha': '${SOURCE_HEAD}'", text)
        self.assertIn("'base_sha': '${base_sha}'", text)
        self.assertIn('repos/${GITHUB_REPOSITORY}/dispatches', text)

    def test_noop_when_materializer_did_not_advance_head(self) -> None:
        text = self.text
        self.assertIn('if [ "$live_head" = "$SOURCE_HEAD" ]; then', text)
        self.assertIn("NOOP: materializer completed without advancing the PR head.", text)

    def test_permission_surface_has_no_pr_write_or_actions_write(self) -> None:
        text = self.text
        self.assertIn("contents: write", text)
        self.assertIn("pull-requests: read", text)
        self.assertNotIn("pull-requests: write", text)
        self.assertNotIn("actions: write", text)


if __name__ == "__main__":
    unittest.main()
