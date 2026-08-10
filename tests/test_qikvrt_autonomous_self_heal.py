# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_autonomous_self_heal",
    ROOT / "tools/qikvrt_autonomous_self_heal.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AutonomousSelfHealTests(unittest.TestCase):
    def test_expected_head_bound_promotion_is_exact_and_fail_closed(self) -> None:
        contract = MODULE.load_contract()
        delegation = MODULE.load_delegation()
        expected = list(MODULE.PROMOTION_CONDITIONS)
        self.assertEqual(
            contract["execution_model"]["promotion"],
            "expected_head_bound_only",
        )
        self.assertEqual(
            contract["promotion_policy"]["unconditional_automatic_merge"],
            "FORBIDDEN",
        )
        self.assertEqual(
            contract["promotion_policy"]["expected_head_bound_promotion"],
            "ALLOWED_ONLY_IF",
        )
        self.assertEqual(contract["promotion_policy"]["conditions"], expected)
        self.assertFalse(
            contract["promotion_policy"]["proposal_workflow_may_merge"]
        )
        self.assertFalse(
            contract["promotion_policy"]["general_auto_merge_authorization"]
        )
        self.assertTrue(
            delegation["promotion_policy"]["standing_delegation"]
        )
        self.assertEqual(
            delegation["promotion_policy"]["conditions"],
            expected,
        )
        forbidden = set(contract["forbidden_effects"])
        self.assertIn("unconditional_automatic_merge", forbidden)
        self.assertIn("unbound_or_stale_head_promotion", forbidden)
        self.assertIn("zenodo_mutation", forbidden)
        self.assertIn("ietf_mutation", forbidden)
        self.assertIn("deployment", forbidden)

    def test_allowlist_is_exactly_handler_owned(self) -> None:
        contract = MODULE.load_contract()
        allowed = MODULE.allowed_paths(contract)
        self.assertIn("anticipation/next-effect.json", allowed)
        self.assertIn("docs/publications/index.json", allowed)
        self.assertIn("docs/publications/index.html", allowed)
        self.assertIn("REPOSITORY_FILE_MANIFEST.json", allowed)
        self.assertNotIn("AI_STATUS.md", allowed)
        self.assertNotIn(
            ".github/workflows/qikvrt_autonomous_self_heal.yml",
            allowed,
        )

    def test_publication_overview_precedes_integrity(self) -> None:
        handlers = MODULE.load_contract()["allowlisted_handlers"]
        order = [handler["failure_class"] for handler in handlers]
        self.assertLess(
            order.index("PUBLICATION_OVERVIEW_DRIFT"),
            order.index("REPOSITORY_NATIVE_INTEGRITY_STALE"),
        )
        publication = next(
            handler
            for handler in handlers
            if handler["failure_class"] == "PUBLICATION_OVERVIEW_DRIFT"
        )
        self.assertEqual(
            publication["failure_signature"],
            "publication overview drift:",
        )

    def test_pr_continuation_is_explicitly_opt_in_and_external_gate_bounded(self) -> None:
        continuation = MODULE.load_contract()["pull_request_continuation"]
        self.assertEqual(
            continuation["opt_in_marker"],
            "<!-- qikvrt-autonomous-self-heal:enabled -->",
        )
        self.assertTrue(continuation["same_repository_only"])
        self.assertTrue(continuation["draft_only"])
        self.assertEqual(continuation["maximum_pull_requests_per_run"], 4)
        self.assertEqual(
            continuation["parallelism"],
            "PATH_DISJOINT_CONFLICT_COMPONENTS",
        )
        self.assertFalse(continuation["blocked_candidate_stalls_independent_component"])
        self.assertIn(
            "IDENTIFIED_HUMAN_PHYSICS_REVIEW_WHEN_REQUIRED",
            continuation["external_gates"],
        )
        self.assertIn(
            "SEPARATE_EXPLICIT_ZENODO_AUTHORIZATION",
            continuation["external_gates"],
        )

    def test_semantic_fingerprint_is_path_and_byte_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "a").write_bytes(b"one")
            (root / "b").write_bytes(b"two")
            with mock.patch.object(MODULE, "ROOT", root):
                first = MODULE.semantic_fingerprint(["a", "b"])
                second = MODULE.semantic_fingerprint(["b", "a"])
                self.assertEqual(first, second)
                (root / "b").write_bytes(b"three")
                self.assertNotEqual(
                    first,
                    MODULE.semantic_fingerprint(["a", "b"]),
                )

    def test_candidate_identity_binds_base_and_fingerprint(self) -> None:
        fingerprint = "1" * 64
        first = MODULE.candidate_identity("a" * 40, fingerprint)
        self.assertEqual(
            first,
            MODULE.candidate_identity("a" * 40, fingerprint),
        )
        self.assertNotEqual(
            first,
            MODULE.candidate_identity("b" * 40, fingerprint),
        )

    def test_non_projection_anticipation_failure_blocks(self) -> None:
        handler = {
            "failure_class": "ANTICIPATION_PROJECTION_DRIFT",
            "probe": ["probe"],
            "repair": ["repair"],
            "failure_signature": "projection drift:",
        }
        result = MODULE.CommandResult(
            ("probe",),
            2,
            "BLOCK",
            "source binding drift",
        )
        with mock.patch.object(MODULE, "run", return_value=result):
            with self.assertRaises(MODULE.SelfHealBlock):
                MODULE.repair_handler(handler)

    def test_generic_failure_signature_blocks_unrecognized_failure(self) -> None:
        handler = {
            "failure_class": "PUBLICATION_OVERVIEW_DRIFT",
            "probe": ["probe"],
            "repair": ["repair"],
            "failure_signature": "publication overview drift:",
        }
        result = MODULE.CommandResult(("probe",), 2, "", "different failure")
        with mock.patch.object(MODULE, "run", return_value=result):
            with self.assertRaises(MODULE.SelfHealBlock):
                MODULE.repair_handler(handler)

    def test_recognized_failure_runs_exact_repair(self) -> None:
        handler = {
            "failure_class": "PUBLICATION_OVERVIEW_DRIFT",
            "probe": ["probe"],
            "repair": ["repair"],
            "failure_signature": "publication overview drift:",
        }
        results = [
            MODULE.CommandResult(
                ("probe",), 2, "publication overview drift: missing", ""
            ),
            MODULE.CommandResult(("repair",), 0, "MATERIALIZED", ""),
        ]
        with mock.patch.object(MODULE, "run", side_effect=results) as mocked:
            value = MODULE.repair_handler(handler)
        self.assertEqual(value["state"], "REPAIRED")
        self.assertEqual(mocked.call_count, 2)


if __name__ == "__main__":
    unittest.main()
