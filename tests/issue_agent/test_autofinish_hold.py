from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/issue-agent-autofinish.yml"


class IssueAgentAutofinishHoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_has_no_repository_release_mutation(self) -> None:
        forbidden = (
            "gh pr merge",
            "gh pr create",
            "git push",
            "/git/refs",
            "refs/tags/",
            "gh release",
            "/releases",
            "gh issue close",
            "contents: write",
            "pull-requests: write",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, self.text)
        self.assertIn('first_blocker:"ISSUE_AGENT_RELEASE_EFFECT_DISABLED"', self.text)
        self.assertIn('repository_or_release_effect:"NONE"', self.text)
        self.assertIn('transport_effect:"ACTIONS_ARTIFACT_UPLOAD"', self.text)
        self.assertNotIn('external_effect:"NONE"', self.text)

    def test_empty_status_rollup_is_never_authority(self) -> None:
        self.assertIn("empty_status_check_rollup_is_authority:false", self.text)
        self.assertIn(
            'exact_head_named_results:{required:true,state:"UNOBSERVED"}', self.text
        )
        self.assertNotIn("statusCheckRollup", self.text)

    def test_divergent_authority_mirror_binding_is_never_authority(self) -> None:
        self.assertIn("exact_heads_required:true", self.text)
        self.assertIn("exact_trees_required:true", self.text)
        self.assertIn("divergent_binding_is_authority:false", self.text)

    def test_reciprocal_receipt_is_required_and_absent(self) -> None:
        self.assertIn('reciprocal_receipt:{required:true,state:"ABSENT"}', self.text)
        self.assertIn("reciprocal_receipt_verified:false", self.text)

    def test_direct_or_lightweight_tags_are_forbidden(self) -> None:
        self.assertIn("annotated_required:true", self.text)
        self.assertIn("direct_or_lightweight_tag_allowed:false", self.text)
        self.assertIn("tag_created:false", self.text)

    def test_separate_marker_only_authorizations_are_required(self) -> None:
        self.assertIn("separate_per_repository:true", self.text)
        self.assertIn("marker_only:true", self.text)
        self.assertIn('marker_authorizations:', self.text)
        self.assertIn('state:"ABSENT"', self.text)


if __name__ == "__main__":
    unittest.main()
