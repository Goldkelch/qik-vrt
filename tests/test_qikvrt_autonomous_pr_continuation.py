# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json"
CONTINUATION = ROOT / ".github/workflows/qikvrt_autonomous_pr_continuation.yml"
VERIFIER = ROOT / ".github/workflows/qikvrt_autonomous_exact_head_verify.yml"


class AutonomousPRContinuationTests(unittest.TestCase):
    def test_contract_is_opt_in_same_repo_draft_and_one_at_a_time(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        value = contract["pull_request_continuation"]
        self.assertEqual(
            value["opt_in_marker"],
            "<!-- qikvrt-autonomous-self-heal:enabled -->",
        )
        self.assertTrue(value["same_repository_only"])
        self.assertTrue(value["draft_only"])
        self.assertEqual(value["maximum_pull_requests_per_run"], 1)
        self.assertEqual(value["history_rewrite"], "FORBIDDEN")
        self.assertEqual(
            value["automatic_promotion"],
            "HOLD_UNTIL_ALL_EXTERNAL_AND_INTERNAL_GATES",
        )

    def test_continuation_preserves_history_and_never_merges_or_force_pushes(self) -> None:
        source = CONTINUATION.read_text(encoding="utf-8")
        self.assertIn("git merge --no-ff --no-commit", source)
        self.assertIn("live_head_before_push", source)
        self.assertIn("refs/heads/${HEAD_REF}", source)
        self.assertNotIn("git push --force", source)
        self.assertNotIn("git push -f", source)
        self.assertNotIn("gh pr merge", source)
        self.assertNotIn("refs/heads/main\"", source)
        self.assertIn("make test", source)
        self.assertIn("qikvrt_autonomous_exact_head_verify", source)

    def test_only_regenerable_projection_conflicts_may_be_resolved(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        policy = contract["pull_request_continuation"][
            "generated_merge_conflict_policy"
        ]
        self.assertEqual(policy["mode"], "ALLOWLIST_ONLY_REGENERATE_IMMEDIATELY")
        self.assertEqual(policy["temporary_resolution_side"], "CURRENT_MAIN")
        self.assertEqual(policy["non_allowlisted_conflict"], "BLOCK")
        self.assertEqual(
            policy["allowed_paths"],
            [
                "REPOSITORY_FILE_MANIFEST.json",
                "REPOSITORY_FILE_MANIFEST.json.sha256",
                "SHA256SUMS.txt",
                "docs/publications/index.html",
                "docs/publications/index.json",
            ],
        )

        source = CONTINUATION.read_text(encoding="utf-8")
        self.assertIn("git diff --name-only --diff-filter=U", source)
        self.assertIn("unexpected_conflicts=\"$(comm -23", source)
        self.assertIn("BLOCK: non-regenerable merge conflicts", source)
        self.assertIn("git merge --abort", source)
        self.assertIn("git checkout --theirs -- \"$path\"", source)
        self.assertIn("generated_conflicts_resolved=true", source)
        self.assertIn("test -s /tmp/qikvrt-pr-self-heal-paths", source)

        merge_position = source.index("git commit --no-edit")
        regeneration_position = source.index(
            "tools/qikvrt_autonomous_self_heal.py apply"
        )
        push_position = source.index('git push origin "HEAD:refs/heads/${HEAD_REF}"')
        self.assertLess(merge_position, regeneration_position)
        self.assertLess(regeneration_position, push_position)

    def test_dispatch_verifier_binds_exact_head_and_posts_a_distinct_status(self) -> None:
        source = VERIFIER.read_text(encoding="utf-8")
        self.assertIn("repository_dispatch", source)
        self.assertIn("qikvrt_autonomous_exact_head_verify", source)
        self.assertIn("test \"$(git rev-parse --verify HEAD^{commit})\" = \"$TARGET_SHA\"", source)
        self.assertIn("make test", source)
        self.assertIn("verify_qce_package.py", source)
        self.assertIn("QIKVRT autonomous exact-head verification", source)
        self.assertNotIn("gh pr merge", source)
        self.assertNotIn("zenodo", source.casefold())
        self.assertNotIn("ietf", source.casefold())

    def test_external_review_and_publication_gates_remain_distinct(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        gates = contract["pull_request_continuation"]["external_gates"]
        self.assertEqual(
            gates,
            [
                "IDENTIFIED_HUMAN_PHYSICS_REVIEW_WHEN_REQUIRED",
                "SEPARATE_EXPLICIT_ZENODO_AUTHORIZATION",
            ],
        )


if __name__ == "__main__":
    unittest.main()
