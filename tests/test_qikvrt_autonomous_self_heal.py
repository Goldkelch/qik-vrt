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
        self.assertIn("REPOSITORY_FILE_MANIFEST.json", allowed)
        self.assertNotIn("AI_STATUS.md", allowed)
        self.assertNotIn(
            ".github/workflows/qikvrt_autonomous_self_heal.yml",
            allowed,
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


if __name__ == "__main__":
    unittest.main()
