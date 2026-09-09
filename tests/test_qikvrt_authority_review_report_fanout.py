# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUESTED_REVIEW_CONTRACT = ROOT / ".github/workflows/qikvrt_requested_review_contract.yml"
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_authority_review_report_fanout",
    ROOT / "tools/qikvrt_authority_review_report_fanout.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AuthorityReviewReportFanoutTests(unittest.TestCase):
    pr_number = 1062
    candidate_head = "b" * 40
    execution_merge_sha = "c" * 40
    fingerprint = "d" * 64

    def artifact(
        self,
        *,
        number: int | None = None,
        head: str | None = None,
        fingerprint: str | None = None,
        expired: bool = False,
    ):
        selected_number = self.pr_number if number is None else number
        selected_head = self.candidate_head if head is None else head
        selected_fingerprint = self.fingerprint if fingerprint is None else fingerprint
        return {
            "name": (
                f"qikvrt-mesh-review-pr-{selected_number}-{selected_head}-"
                f"{selected_fingerprint}"
            ),
            "expired": expired,
        }

    def test_artifact_binds_candidate_not_direct_review_merge_execution_sha(self):
        binding = MODULE.source_artifact_binding(
            artifacts={"artifacts": [self.artifact()]},
        )
        self.assertEqual(binding["pr_number"], self.pr_number)
        self.assertEqual(binding["head_sha"], self.candidate_head)
        self.assertEqual(binding["evidence_fingerprint"], self.fingerprint)
        self.assertNotEqual(binding["head_sha"], self.execution_merge_sha)

    def test_advisory_workflow_run_pr_association_is_not_candidate_authority(self):
        binding = MODULE.source_artifact_binding(
            artifacts={"artifacts": [self.artifact()]},
        )
        self.assertEqual(binding["pr_number"], self.pr_number)

    def test_missing_expired_or_ambiguous_evidence_artifact_holds(self):
        cases = {
            "missing": [],
            "expired": [self.artifact(expired=True)],
            "ambiguous": [
                self.artifact(),
                self.artifact(fingerprint="e" * 64),
            ],
        }
        for name, artifacts in cases.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                    MODULE.AuthorityReviewReportBindingError,
                    "SOURCE_RUN_ARTIFACT_MISSING_OR_AMBIGUOUS",
                ):
                    MODULE.source_artifact_binding(
                        artifacts={"artifacts": artifacts},
                    )

    def test_workflow_is_sealed_against_cross_repository_effects(self):
        workflow = (
            ROOT / ".github/workflows/qikvrt_authority_review_report_fanout.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("source_artifact_binding", workflow)
        self.assertIn("actions/runs/{source_run_id}/artifacts", workflow)
        self.assertIn("artifact-bound candidate head differs", workflow)
        self.assertIn("match.group(3) == fingerprint", workflow)
        self.assertNotIn("SOURCE_HEAD:", workflow)
        self.assertNotIn("SOURCE_PULL_REQUESTS:", workflow)
        self.assertNotIn('os.environ["SOURCE_HEAD"]', workflow)
        self.assertIn("if: ${{ false }}", workflow)
        self.assertNotIn("MESH_TOKEN:", workflow)
        self.assertIn("cross-repository repository_dispatch route", workflow)
        self.assertNotIn("/dispatches", workflow)
        self.assertNotIn("issues: write", workflow)
        self.assertNotIn("--method POST", workflow)

    def test_contract_shell_avoids_github_expression_rewriting(self):
        contract = REQUESTED_REVIEW_CONTRACT.read_text(encoding="utf-8")
        start = contract.index("      - name: Verify event, recovery, identity and promotion bindings")
        shell = contract[start:]
        self.assertNotIn("${{", shell)
        self.assertIn(
            "sealed until a separately authorized, brokered cross-repository delivery",
            shell,
        )


if __name__ == "__main__":
    unittest.main()
