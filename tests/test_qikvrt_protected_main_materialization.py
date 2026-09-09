# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Protected-main persistence must use a candidate PR, never a direct push."""

from __future__ import annotations

import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
UNIVERSAL = ROOT / ".github/workflows/qikvrt_universal_terminal_materialize.yml"
EVIDENCE = ROOT / ".github/workflows/qikvrt_batch04_integrity.yml"
BATCH003 = ROOT / ".github/workflows/qikvrt_batch003_remaining_disposition.yml"
CONTRACT = ROOT / "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"


class ProtectedMainMaterializationTests(unittest.TestCase):
    def test_universal_materializer_stops_on_stale_subject_and_uses_draft_pr(self) -> None:
        workflow = UNIVERSAL.read_text(encoding="utf-8")
        self.assertIn("id: trusted-main", workflow)
        self.assertIn("echo \"current=false\" >> \"$GITHUB_OUTPUT\"", workflow)
        self.assertIn("HOLD_UNVERIFIED stale subject=", workflow)
        self.assertIn("exit 2", workflow)
        self.assertIn("if: steps.trusted-main.outputs.current == 'true'", workflow)
        self.assertIn("pull-requests: write", workflow)
        self.assertIn("automation/universal-terminal-materialization-", workflow)
        self.assertIn("git push origin \"HEAD:refs/heads/$branch\"", workflow)
        self.assertIn("gh pr create", workflow)
        self.assertIn("--draft", workflow)
        self.assertIn("gh pr view", workflow)
        self.assertIn("baseRefOid", workflow)
        self.assertIn("tools/qikvrt_candidate_pr_receipt.py", workflow)
        self.assertIn("Reobserved existing universal-terminal draft candidate", workflow)
        self.assertNotIn("git push origin HEAD:main", workflow)

    def test_repository_evidence_materializer_routes_main_delta_to_draft_pr(self) -> None:
        workflow = EVIDENCE.read_text(encoding="utf-8")
        self.assertIn("pull-requests: write", workflow)
        self.assertIn('if [ "$TARGET_REF" = main ]; then', workflow)
        self.assertIn("automation/repository-evidence-", workflow)
        self.assertIn("git push origin \"HEAD:refs/heads/$candidate_branch\"", workflow)
        self.assertIn("gh pr create", workflow)
        self.assertIn("--draft", workflow)
        self.assertIn("remote_main_before_pr", workflow)
        self.assertIn("gh pr view", workflow)
        self.assertIn("baseRefOid", workflow)
        self.assertIn("tools/qikvrt_candidate_pr_receipt.py", workflow)
        self.assertIn("Reobserved existing repository-evidence draft candidate", workflow)

    def test_repository_evidence_materializer_is_a_declared_writer(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        writers = contract["dispatch_policy"]["writer_workflow_names"]
        self.assertEqual(writers.count("QIKVRT Batch-003 remaining subject disposition"), 1)
        self.assertEqual(writers.count("QIKVRT repository evidence materialization"), 1)
        self.assertEqual(writers.count("QIKVRT universal terminal materialization"), 1)

    def test_batch003_materializer_routes_manual_main_to_draft_pr(self) -> None:
        workflow = BATCH003.read_text(encoding="utf-8")
        self.assertIn("pull-requests: write", workflow)
        self.assertIn('if [ "$TARGET_REF" = main ]; then', workflow)
        self.assertIn("automation/batch003-repository-evidence-", workflow)
        self.assertIn("git push origin \"HEAD:refs/heads/$candidate_branch\"", workflow)
        self.assertIn("gh pr create", workflow)
        self.assertIn("--draft", workflow)
        self.assertIn("tools/qikvrt_candidate_pr_receipt.py", workflow)
        self.assertIn("Reobserved existing Batch-003 draft candidate", workflow)

    def test_every_candidate_receipt_binds_materialized_tree_and_direct_source_parent(self) -> None:
        for workflow_path in (UNIVERSAL, EVIDENCE, BATCH003):
            workflow = workflow_path.read_text(encoding="utf-8")
            receipt_calls = workflow.count("tools/qikvrt_candidate_pr_receipt.py")
            self.assertEqual(receipt_calls, 2, workflow_path.name)
            self.assertIn('expected_tree="$(git write-tree)"', workflow, workflow_path.name)
            self.assertEqual(
                workflow.count('--expected-tree "$expected_tree"'),
                receipt_calls,
                workflow_path.name,
            )
            self.assertEqual(
                workflow.count("--repository ."),
                receipt_calls,
                workflow_path.name,
            )
            self.assertIn(
                'git fetch --no-tags origin "refs/heads/',
                workflow,
                workflow_path.name,
            )


if __name__ == "__main__":
    unittest.main()
