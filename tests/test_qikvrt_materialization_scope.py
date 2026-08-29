# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_materialization_scope",
    ROOT / "tools/qikvrt_materialization_scope.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
WORKFLOW = ROOT / ".github/workflows/qikvrt_batch04_integrity.yml"
BATCH003_WORKFLOW = (
    ROOT / ".github/workflows/qikvrt_batch003_remaining_disposition.yml"
)


class MaterializationScopeTests(unittest.TestCase):
    def test_unrelated_internal_repair_skips_all_expensive_optional_generators(self) -> None:
        result = MODULE.classify(
            [
                ".github/workflows/qikvrt_autonomous_self_heal.yml",
                "tools/qikvrt_autonomous_pre_effect_controller.py",
                "tests/test_qikvrt_autonomous_pre_effect_controller.py",
                "tests/test_qikvrt_continuous_auto_repair.py",
            ]
        )
        self.assertFalse(result["full"])
        self.assertFalse(result["formalization"])
        self.assertFalse(result["content_disposition"])
        self.assertFalse(result["aphorism"])
        self.assertTrue(result["integrity"])
        self.assertTrue(result["complete_repository_gates"])
        self.assertFalse(result["claims"]["M68000_EXECUTED"])
        self.assertFalse(result["claims"]["WORKFLOW_ACCELERATED_BY_M68000"])

    def test_each_domain_is_triggered_only_by_its_causal_inputs(self) -> None:
        formal = MODULE.classify(
            ["formalization/QIKVRT_Formalization_v2.0/claims/CLAIM_GRAPH.json"]
        )
        self.assertTrue(formal["formalization"])
        self.assertFalse(formal["content_disposition"])
        self.assertFalse(formal["aphorism"])

        content = MODULE.classify(
            ["tools/qikvrt_content_disposition_batch_003_dispatch.py"]
        )
        self.assertFalse(content["formalization"])
        self.assertTrue(content["content_disposition"])
        self.assertFalse(content["aphorism"])

        aphorism = MODULE.classify(["tools/qikvrt_aphorism_corpus_v2.py"])
        self.assertFalse(aphorism["formalization"])
        self.assertFalse(aphorism["content_disposition"])
        self.assertTrue(aphorism["aphorism"])

    def test_control_or_unsafe_path_fails_safe_to_full_materialization(self) -> None:
        for path in (
            ".github/workflows/qikvrt_batch04_integrity.yml",
            ".github/workflows/qikvrt_batch003_remaining_disposition.yml",
            "../ambiguous",
        ):
            result = MODULE.classify([path])
            self.assertTrue(result["full"], path)
            self.assertTrue(result["formalization"], path)
            self.assertTrue(result["content_disposition"], path)
            self.assertTrue(result["aphorism"], path)

    def test_explicit_full_mode_preserves_manual_and_ambiguous_recovery(self) -> None:
        result = MODULE.classify([], force_full=True)
        self.assertTrue(result["full"])
        self.assertTrue(result["formalization"])
        self.assertTrue(result["content_disposition"])
        self.assertTrue(result["aphorism"])

    def test_workflow_binds_scope_before_expensive_generators(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        classifier = "- name: Classify deterministic materialization scope"
        self.assertIn(classifier, workflow)
        self.assertIn("id: scope", workflow)
        self.assertIn("tools/qikvrt_materialization_scope.py", workflow)
        self.assertIn("git diff --name-only -z", workflow)
        self.assertIn("fetch-depth: 2", workflow)
        self.assertLess(
            workflow.index(classifier),
            workflow.index("- name: Materialize completed manuscript evidence when present"),
        )

        guarded = {
            "Materialize completed manuscript evidence when present": "formalization",
            "Rebuild deterministic formalization release bundle when present": "formalization",
            "Refresh most advanced content-disposition status when present": "content_disposition",
            "Provision and verify aphorism publication runtime when present": "aphorism",
            "Materialize aphorism-corpus scientific assessment when present": "aphorism",
        }
        for name, output in guarded.items():
            token = (
                f"- name: {name}\n"
                f"        if: steps.scope.outputs.{output} == 'true'"
            )
            self.assertIn(token, workflow)

    def test_batch003_writer_is_not_triggered_or_persisted_by_unrelated_prs(self) -> None:
        workflow = BATCH003_WORKFLOW.read_text(encoding="utf-8")
        pull_request = workflow.index("  pull_request:")
        dispatch = workflow.index("  workflow_dispatch:")
        trigger = workflow[pull_request:dispatch]
        self.assertIn("    paths:\n", trigger)
        required_patterns = (
            '      - ".github/workflows/qikvrt_batch003_remaining_disposition.yml"',
            '      - "tools/qikvrt_content_disposition_*.py"',
            '      - "tools/qikvrt_batch003_*.py"',
            '      - "tests/test_content_disposition_batch_003_*.py"',
            '      - "release/zenodo-corpus-proof-2026-07-28/canonical-union/**"',
            '      - "work-units/**"',
            '      - "AI_PROGRESS.json"',
            '      - "AI_STATUS.md"',
        )
        for pattern in required_patterns:
            self.assertIn(pattern, trigger)
        self.assertNotIn('      - "**"', trigger)
        self.assertNotIn('      - "*"', trigger)
        self.assertIn("  cancel-in-progress: false", workflow)
        for name in (
            "Regenerate and verify repository integrity",
            "Run complete repository gates",
            "Persist exact evidence head",
        ):
            self.assertIn(
                f"- name: {name}\n"
                "        if: github.event_name != 'pull_request'",
                workflow,
            )

    def test_integrity_and_complete_gates_remain_unconditional(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        integrity = workflow.index("- name: Regenerate and verify repository integrity")
        gates = workflow.index("- name: Run complete repository gates before persistence")
        commit = workflow.index("- name: Commit materialized repository evidence")
        self.assertLess(integrity, gates)
        self.assertLess(gates, commit)
        self.assertIn("make test", workflow[gates:commit])
        self.assertNotIn("if: steps.scope.outputs", workflow[integrity:commit])


if __name__ == "__main__":
    unittest.main()
