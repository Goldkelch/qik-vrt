import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/SELF_CLOSING_EXECUTION_LOOP_V1.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_self_closing_execution_loop.yml"


class SelfClosingExecutionLoopTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_fail_closed_writer_invariants_are_normative(self):
        inv = self.policy["invariants"]
        self.assertEqual(inv["productive_writer_limit"], 1)
        for key in (
            "exact_source_head_before_every_effect",
            "reobserve_after_every_effect",
            "competing_productive_writer_forbidden",
            "force_push_forbidden",
            "history_rewrite_forbidden",
            "predecessor_gate_transfer_forbidden",
            "failed_gate_masking_forbidden",
            "permission_escalation_forbidden",
            "credential_escalation_forbidden",
            "platform_quota_bypass_forbidden",
            "external_effect_without_separate_authority_forbidden",
            "ambiguous_repair_is_hold",
        ):
            self.assertTrue(inv[key], key)

    def test_integrity_repair_scope_is_exactly_three_projection_files(self):
        repair = self.policy["deterministic_repairs"]["integrity_projection"]
        self.assertTrue(repair["enabled"])
        self.assertEqual(
            repair["allowed_paths"],
            [
                "REPOSITORY_FILE_MANIFEST.json",
                "REPOSITORY_FILE_MANIFEST.json.sha256",
                "SHA256SUMS.txt",
            ],
        )
        self.assertEqual(repair["required_change_set"], "EXACT_ALLOWED_PATH_SET")
        self.assertFalse(repair["external_effect"])

    def test_workflow_reobserves_exact_head_and_uses_one_serial_writer(self):
        self.assertIn("cancel-in-progress: false", self.workflow)
        self.assertIn("ref: ${{ env.SOURCE_SHA }}", self.workflow)
        self.assertIn('test "$remote_head" = "$SOURCE_SHA"', self.workflow)
        self.assertIn('test "$parent" = "$SOURCE_SHA"', self.workflow)
        self.assertIn('git push origin "HEAD:refs/heads/$SOURCE_REF"', self.workflow)
        self.assertNotIn("--force", self.workflow)
        self.assertNotIn("--force-with-lease", self.workflow)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", self.workflow)

    def test_workflow_can_only_commit_integrity_projection_trio(self):
        for path in (
            "REPOSITORY_FILE_MANIFEST.json",
            "REPOSITORY_FILE_MANIFEST.json.sha256",
            "SHA256SUMS.txt",
        ):
            self.assertIn(path, self.workflow)
        self.assertIn('test "$(git diff --cached --name-only | wc -l)" -eq 3', self.workflow)
        self.assertIn("python3 -B tools/qikvrt_integrity.py verify", self.workflow)
        self.assertIn("git diff --cached --check", self.workflow)

    def test_atari_delivery_cannot_claim_completion_before_return_ack(self):
        atari = self.policy["atari_vertical_delivery_invariant"]
        self.assertTrue(atari["required"])
        self.assertTrue(atari["completion_requires_all_states"])
        self.assertEqual(
            atari["states"][-1],
            "ACK_RETURNED_TO_AUTHORITY_CONTEXT",
        )
        self.assertTrue(atari["requested_is_not_executed"])
        self.assertTrue(atari["executed_is_not_observed"])
        self.assertTrue(atari["observed_is_not_acknowledged"])
        self.assertTrue(atari["transport_ack_is_not_effect_ack"])

    def test_policy_cannot_be_weakened_in_place(self):
        imm = self.policy["immutability"]
        self.assertTrue(imm["this_version_may_not_be_weakened_in_place"])
        self.assertTrue(imm["semantic_weakening_requires_explicit_product_owner_authorized_successor"])
        self.assertTrue(imm["successor_must_preserve_or_strengthen_fail_closed_boundaries"])


if __name__ == "__main__":
    unittest.main()
